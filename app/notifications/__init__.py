"""Push notification module.

Provides provider-agnostic notification delivery via NotificationService.
"""

from .router import router
from .service import NotificationService

__all__ = ["router", "NotificationService"]
