"""
Repositories package.

Re-exports the public surface so consumers import from `app.repositories`
rather than from concrete module paths.
"""

from app.repositories.notification_repository import NotificationRepository  # noqa: F401

__all__ = ["NotificationRepository"]
