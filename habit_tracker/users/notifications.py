"""Unified notification helper.

`notify()` is the single entry point for telling a user something happened:
it persists an in-app Notification row AND fires an Expo push to their devices.
Use this everywhere instead of creating Notification objects directly so push
delivery stays consistent.
"""
import logging

logger = logging.getLogger(__name__)


def notify(user, title, message, ntype="INFO", data=None, push=True):
    """Create an in-app notification and (optionally) send a push.

    Returns the created Notification instance.
    """
    from .models import Notification

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=ntype,
    )

    if push:
        try:
            from .push import send_push_to_user
            payload = {"type": ntype, "notification_id": str(notification.id)}
            if data:
                payload.update(data)
            send_push_to_user(user, title, message, payload)
        except Exception as exc:
            logger.warning("Push dispatch failed for %s: %s", user, exc)

    return notification
