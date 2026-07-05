import logging
from dataclasses import dataclass

from app.notifications.repository import NotificationRepository
from app.notifications.providers.base import NotificationProvider

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    total: int = 0
    sent: int = 0
    failed: int = 0


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        providers: dict[str, NotificationProvider],
    ):
        self._repository = repository
        self._providers = providers

    async def send_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> SendResult:
        devices = self._repository.get_active_devices(user_id)
        if not devices:
            logger.info("No devices found for user %d", user_id)
            return SendResult()

        results: list[bool] = []

        for device in devices:
            provider = self._providers.get(device.platform)
            if provider is None:
                logger.warning("No provider for platform: %s", device.platform)
                continue

            result = await provider.send(
                token=device.push_token,
                title=title,
                body=body,
                data=data,
            )

            self._repository.save_history(
                user_id=user_id,
                title=title,
                body=body,
                data=data,
                provider=device.platform,
                status="sent" if result.success else "failed",
                provider_response=result.provider_response,
                error=result.error,
            )

            if not result.success and result.error in {"NotRegistered", "InvalidToken"}:
                logger.info("Removing %s device %d for user %d", result.error, device.id, user_id)
                self._repository.delete_device(device.id)

            results.append(result.success)

        return SendResult(
            total=len(devices),
            sent=sum(1 for r in results if r),
            failed=sum(1 for r in results if not r),
        )
