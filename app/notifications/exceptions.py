class NotificationError(Exception):
    """Base exception for notification errors."""
    ...


class ProviderNotAvailable(NotificationError):
    """Raised when no provider is configured for a platform."""
    ...


class InvalidToken(NotificationError):
    """Raised when a push token is invalid or unregistered."""
    ...
