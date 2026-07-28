"""
NotificationService — all business logic for the notification domain.

Responsibilities:
  - Validate input (type, title, body) beyond what Pydantic enforces.
  - Coordinate with NotificationRepository for all persistence.
  - Build paginated NotificationList responses.
  - Enforce that service methods always receive tenant context — never
    raw request objects.

Rules:
  - Never import FastAPI here. No Request, no HTTPException.
  - Never access the DB directly. Always go through the repository.
  - Raise domain exceptions (NotFoundError, ForbiddenError,
    ValidationError) — the exception handlers in main.py translate these.
"""

import math

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification_schema import (
    NOTIFICATION_TYPES,
    NotificationCreate,
    NotificationList,
    NotificationRead,
    UnreadCountRead,
)


class NotificationService:
    """
    Orchestrates notification business logic.

    Instantiated per-request in route handlers, receiving the DB session
    and tenant context via FastAPI dependency injection.
    """

    def __init__(self, db: Session) -> None:
        self._repo = NotificationRepository(db)

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def create(
        self,
        tenant_id: str,
        payload: NotificationCreate,
    ) -> NotificationRead:
        """
        Create a new notification.

        The tenant_id always comes from TenantContext — callers cannot
        supply or override it via the request body.

        Note: user_id in the payload is the *target* user (who should
        receive this notification), not the caller. It is intentionally
        accepted in the body so that admin/system callers can create
        notifications targeted at specific users.

        Raises:
            ValidationError if the type is not in NOTIFICATION_TYPES
                            (belt-and-suspenders beyond the Pydantic Literal).
        """
        if payload.type not in NOTIFICATION_TYPES:
            raise ValidationError(
                f"Invalid notification type '{payload.type}'. "
                f"Allowed: {sorted(NOTIFICATION_TYPES)}"
            )

        notification = self._repo.create(
            tenant_id=tenant_id,
            type=payload.type,
            title=payload.title,
            body=payload.body,
            user_id=payload.user_id,
        )
        return NotificationRead.from_orm_model(notification)

    # ------------------------------------------------------------------
    # list_notifications
    # ------------------------------------------------------------------

    def list_notifications(
        self,
        tenant_id: str,
        user_id: str | None,
        page: int = 1,
        size: int = 20,
    ) -> NotificationList:
        """
        Return a paginated, sorted list of notifications visible to
        (tenant_id, user_id).

        Ordering: unread first, then newest first within each group.
        This is enforced at the repository layer and never re-sorted here
        so the query plan remains predictable.

        Args:
            page  : 1-based page number.
            size  : items per page.
        """
        offset = (page - 1) * size
        notifications, total = self._repo.find_visible(
            tenant_id=tenant_id,
            user_id=user_id,
            offset=offset,
            limit=size,
        )

        total_pages = max(1, math.ceil(total / size)) if size > 0 else 1

        return NotificationList(
            items=[NotificationRead.from_orm_model(n) for n in notifications],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    # ------------------------------------------------------------------
    # get_unread_count
    # ------------------------------------------------------------------

    def get_unread_count(
        self,
        tenant_id: str,
        user_id: str | None,
    ) -> UnreadCountRead:
        """Return the unread notification count for the bell badge."""
        count = self._repo.count_unread(tenant_id=tenant_id, user_id=user_id)
        return UnreadCountRead(unread_count=count)

    # ------------------------------------------------------------------
    # mark_read
    # ------------------------------------------------------------------

    def mark_read(
        self,
        notification_id: str,
        tenant_id: str,
        user_id: str | None,
    ) -> NotificationRead:
        """
        Mark a single notification as read.

        Raises:
            NotFoundError  — notification does not exist in this tenant.
            ForbiddenError — notification exists but caller cannot see it.
        """
        notification = self._repo.mark_read(
            notification_id=notification_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return NotificationRead.from_orm_model(notification)

    # ------------------------------------------------------------------
    # mark_all_read
    # ------------------------------------------------------------------

    def mark_all_read(
        self,
        tenant_id: str,
        user_id: str | None,
    ) -> dict:
        """
        Mark all visible unread notifications as read.

        Returns a summary dict so the API can confirm how many were updated.
        """
        updated = self._repo.mark_all_read(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return {"updated": updated}
