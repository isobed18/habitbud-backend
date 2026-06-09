"""Project-wide DRF exception handler.

DRF's default handler turns known API exceptions (validation, auth, 404, throttle)
into clean JSON, but lets *unexpected* exceptions (IntegrityError, KeyError, etc.)
bubble up to Django -> HTML 500 / opaque crash for the client. This wraps it so
every unhandled error becomes a clean JSON 500, fully logged server-side.
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('django.request')


def custom_exception_handler(exc, context):
    # Let DRF handle the cases it knows about (ValidationError -> 400, etc.).
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # Anything else is an unexpected server error: log the full traceback and
    # return a clean JSON body instead of an HTML stack trace.
    view = context.get('view').__class__.__name__ if context.get('view') else '?'
    logger.exception('Unhandled error in %s: %s', view, exc)

    body = {'error': 'Sunucu hatası. Lütfen tekrar deneyin.'}
    if settings.DEBUG:
        body['detail'] = f'{exc.__class__.__name__}: {exc}'  # dev-only diagnostics
    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
