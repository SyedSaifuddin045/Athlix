import json
import logging

from firebase_admin import credentials, initialize_app, messaging

from app.notifications.exceptions import ProviderNotAvailable
from .base import NotificationProvider, ProviderResult

logger = logging.getLogger(__name__)


class FCMProvider(NotificationProvider):
    """Send push notifications via Firebase Cloud Messaging HTTP v1 API."""

    def __init__(self, service_account_info: dict):
        try:
            cred = credentials.Certificate(service_account_info)
            self._app = initialize_app(credential=cred)
            logger.info("FCM initialized (project=%s)", service_account_info.get("project_id"))
        except Exception as exc:
            logger.critical("FCM initialization failed: %s", exc)
            raise ProviderNotAvailable(f"FCM init failed: {exc}") from exc

    async def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> ProviderResult:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
            )
            response = messaging.send(message)
            return ProviderResult(success=True, provider_response=response)
        except messaging.UnregisteredError as exc:
            logger.warning("FCM token unregistered: %s", exc)
            return ProviderResult(success=False, error="NotRegistered")
        except messaging.InvalidArgumentError as exc:
            logger.warning("FCM invalid token: %s", exc)
            return ProviderResult(success=False, error="InvalidToken")
        except Exception as exc:
            logger.error("FCM send failed: %s", exc)
            return ProviderResult(success=False, error=str(exc))
