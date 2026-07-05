from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    success: bool
    provider_response: str | None = None
    error: str | None = None


class NotificationProvider(ABC):
    """Abstract interface for push notification providers."""

    @abstractmethod
    async def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> ProviderResult:
        """Send a push notification to the given device token."""
        ...
