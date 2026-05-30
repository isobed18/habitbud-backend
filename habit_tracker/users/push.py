"""Expo push notification helper.

Sends notifications to devices via the Expo Push API. No FCM/APNs keys are
required for Expo-managed apps — Expo brokers delivery. See:
https://docs.expo.dev/push-notifications/sending-notifications/
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _is_expo_token(token: str) -> bool:
    return bool(token) and token.startswith(("ExponentPushToken", "ExpoPushToken"))


def send_push(tokens, title, body, data=None):
    """Send one push message to a list of Expo tokens.

    Returns True if the request was dispatched, False otherwise. Never raises —
    push delivery must not break the request/response cycle.
    """
    tokens = [t for t in (tokens or []) if _is_expo_token(t)]
    if not tokens:
        return False

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
            "data": data or {},
        }
        for token in tokens
    ]

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    access_token = os.getenv("EXPO_ACCESS_TOKEN")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        resp = requests.post(EXPO_PUSH_URL, json=messages, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("Expo push failed: %s %s", resp.status_code, resp.text[:300])
            return False
        return True
    except Exception as exc:  # network errors, timeouts — stay silent
        logger.warning("Expo push exception: %s", exc)
        return False


def send_push_to_user(user, title, body, data=None):
    """Push to all devices registered by a user."""
    tokens = list(user.device_tokens.values_list("token", flat=True))
    return send_push(tokens, title, body, data)
