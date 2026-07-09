"""
Schemas package.

Re-exports the public surface so consumers import from `app.schemas`
rather than from concrete module paths.
"""

from app.schemas.notification_schema import (  # noqa: F401
    NOTIFICATION_TYPES,
    NotificationCreate,
    NotificationList,
    NotificationRead,
    NotificationType,
    UnreadCountRead,
)

__all__ = [
    "NOTIFICATION_TYPES",
    "NotificationCreate",
    "NotificationList",
    "NotificationRead",
    "NotificationType",
    "UnreadCountRead",
]
