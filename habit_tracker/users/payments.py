"""Purchase verification for paid users (App Store / Google Play).

Flow: the app completes a purchase with the store SDK (e.g. react-native-iap /
expo-iap), then POSTs the receipt to /users/api/verify-purchase/. We verify it
SERVER-SIDE with the store, record a Purchase row, and flip user.is_paid.
Never trust the client's word for a purchase.

Apple  — implemented via the verifyReceipt endpoint (works for both sandbox and
         production; needs APPLE_SHARED_SECRET for auto-renewing subscriptions).
Google — requires a Play service account; the hook is here with clear TODOs
         (purchases.products/subscriptions GET via androidpublisher API).
"""
import logging
import os

import requests

logger = logging.getLogger('habit_tracker')

APPLE_PROD_URL = 'https://buy.itunes.apple.com/verifyReceipt'
APPLE_SANDBOX_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'


class VerificationResult:
    def __init__(self, ok, transaction_id=None, product_id=None, error=None, raw=None):
        self.ok = ok
        self.transaction_id = transaction_id
        self.product_id = product_id
        self.error = error
        self.raw = raw or {}


def verify_apple(receipt_data: str) -> VerificationResult:
    """Validate a base64 App Store receipt with Apple.

    Per Apple's guidance: try production first; on status 21007 ("sandbox
    receipt sent to production") retry against the sandbox.
    """
    secret = os.getenv('APPLE_SHARED_SECRET', '')
    payload = {'receipt-data': receipt_data, 'exclude-old-transactions': True}
    if secret:
        payload['password'] = secret

    try:
        resp = requests.post(APPLE_PROD_URL, json=payload, timeout=15)
        data = resp.json()
        if data.get('status') == 21007:
            resp = requests.post(APPLE_SANDBOX_URL, json=payload, timeout=15)
            data = resp.json()
    except Exception as exc:
        logger.warning('Apple receipt verification request failed: %s', exc)
        return VerificationResult(False, error='apple_unreachable')

    status = data.get('status')
    if status != 0:
        return VerificationResult(False, error=f'apple_status_{status}', raw=data)

    # Latest transaction wins (subscriptions put them in latest_receipt_info).
    infos = data.get('latest_receipt_info') or data.get('receipt', {}).get('in_app') or []
    if not infos:
        return VerificationResult(False, error='apple_no_transactions', raw=data)
    last = max(infos, key=lambda i: int(i.get('purchase_date_ms', 0)))
    return VerificationResult(
        True,
        transaction_id=last.get('transaction_id'),
        product_id=last.get('product_id'),
        raw=data,
    )


def verify_google(product_id: str, purchase_token: str) -> VerificationResult:
    """Validate a Play purchase. Requires a Google service account.

    TODO to enable:
      1. Play Console -> create a service account with 'View financial data'.
      2. Save its JSON key, set GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=<path> in .env.
      3. pip install google-api-python-client google-auth, then call
         androidpublisher.purchases().products().get(packageName, productId,
         token) and treat purchaseState == 0 as valid.
    """
    if not os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'):
        return VerificationResult(False, error='google_unconfigured')
    # Placeholder until the service account is provisioned (see TODO above).
    return VerificationResult(False, error='google_not_implemented')


def verify(provider: str, *, receipt=None, product_id=None, purchase_token=None) -> VerificationResult:
    if provider == 'apple':
        if not receipt:
            return VerificationResult(False, error='missing_receipt')
        return verify_apple(receipt)
    if provider == 'google':
        if not (product_id and purchase_token):
            return VerificationResult(False, error='missing_token')
        return verify_google(product_id, purchase_token)
    return VerificationResult(False, error='unknown_provider')
