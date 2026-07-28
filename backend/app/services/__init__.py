"""
Services package.

Re-exports the public surface so consumers import from `app.services`
rather than from concrete module paths.
"""

from app.services.notification_service import NotificationService  # noqa: F401
from app.services.event_service import EventService  # noqa: F401

__all__ = ["NotificationService", "EventService"]
