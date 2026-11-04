"""
Push notifications to the Scout Treasury Android app through Firebase Cloud Messaging.

Set FIREBASE_CREDENTIALS to the contents of a Firebase service-account JSON key.
Without it, notifications are skipped and the rest of the app works normally.
"""
import json
import logging
import os

import database

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    raw = os.environ.get('FIREBASE_CREDENTIALS', '').strip()
    if not raw:
        return None

    import firebase_admin
    from firebase_admin import credentials

    _firebase_app = firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    return _firebase_app


def is_configured():
    return bool(os.environ.get('FIREBASE_CREDENTIALS', '').strip())


def notify_email(email, messages):
    """
    Sends a notification to every phone registered for `email`.
    `messages` maps a language code ('en' / 'ar') to a (title, body) tuple.
    Never raises: a failed push must not break the web request.
    """
    try:
        app = _get_firebase_app()
        if app is None:
            return 0

        from firebase_admin import messaging

        sent = 0
        for device in database.get_devices(email):
            title, body = messages.get(device['language']) or messages['en']
            message = messaging.Message(
                token=device['token'],
                notification=messaging.Notification(title=title, body=body),
                android=messaging.AndroidConfig(priority='high'),
            )
            try:
                messaging.send(message, app=app)
                sent += 1
            except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
                # The app was uninstalled or the token belongs to another project
                database.delete_device(device['token'])
            except Exception:
                logger.exception('Push to one device failed')
        return sent
    except Exception:
        logger.exception('Push notification failed')
        return 0
