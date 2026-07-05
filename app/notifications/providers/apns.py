"""APNs provider placeholder — implement with h2 + api.push.apple.com."""

from .base import NotificationProvider, ProviderResult


class APNsProvider(NotificationProvider):
    """Placeholder for Apple Push Notification service."""

    async def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> ProviderResult:
        raise NotImplementedError("APNs not yet implemented")
