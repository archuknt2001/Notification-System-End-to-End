"""
NotificationRepository — the only layer that touches the database.

Rules:
  - Every method takes tenant_id as its first argument.
  - tenant_id is ALWAYS applied as the first filter — cross-tenant
    access is structurally impossible from within this class.
  - No raw SQL. All queries go through SQLAlchemy ORM.
  - Controllers and services never import Session or query the DB directly.

Visibility rule (mirrors the spec):
  A notification is visible to (tenant_id, user_id) when:
    notification.tenant_id == tenant_id
    AND (notification.user_id IS NULL OR notification.user_id == user_id)

  user_id = None means a tenant-level caller — sees tenant-wide
  notifications only (user_id IS NULL rows).
"""

from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.notification import Notification


class NotificationRepository:
    """
    All database operations for the Notification model.

    Instantiated per-request inside the service layer, with the
    SQLAlchemy Session provided via FastAPI dependency injection.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _visibility_filter(self, tenant_id: str, user_id: str | None):
        """
        Returns a SQLAlchemy filter expression that enforces the
        visibility rule for the given (tenant_id, user_id) pair.

        A notification is visible when:
          tenant_id matches
          AND (user_id IS NULL  ← tenant-wide
               OR user_id matches ← user-specific)
        """
        tenant_filter = Notification.tenant_id == tenant_id

        if user_id is not None:
            user_filter = or_(
                Notification.user_id.is_(None),
                Notification.user_id == user_id,
            )
        else:
            # Tenant-level caller: only tenant-wide notifications
            user_filter = Notification.user_id.is_(None)

        return and_(tenant_filter, user_filter)

    # ------------------------------------------------------------------
    # 1. create
    # ------------------------------------------------------------------

    def create(
        self,
        tenant_id: str,
        type: str,
        title: str,
        body: str,
        user_id: str | None = None,
    ) -> Notification:
        """
        Persist a new notification and return the saved instance.

        Args:
            tenant_id : owning tenant — mandatory.
            type      : notification type string (validated at service layer).
            title     : short human-readable title.
            body      : full notification body.
            user_id   : target user, or None for a tenant-wide notification.
        """
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            read=False,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(notification)
        self._db.commit()
        self._db.refresh(notification)
        return notification

    # ------------------------------------------------------------------
    # 2. find_visible
    # ------------------------------------------------------------------

    def find_visible(
        self,
        tenant_id: str,
        user_id: str | None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Notification], int]:
        """
        Return notifications visible to (tenant_id, user_id).

        Ordering: unread first, then newest first within each group.
        This matches the spec: "Unread first, Newest first".

        Returns:
            (items, total) — the page of results and the total count
            of matching records (used to build pagination metadata).
        """
        base_query = self._db.query(Notification).filter(
            self._visibility_filter(tenant_id, user_id)
        )

        total: int = base_query.count()

        items: list[Notification] = (
            base_query
            .order_by(
                Notification.read.asc(),          # unread (False=0) first
                Notification.created_at.desc(),   # newest first within group
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        return items, total

    # ------------------------------------------------------------------
    # 3. find_by_id
    # ------------------------------------------------------------------

    def find_by_id(
        self,
        notification_id: str,
        tenant_id: str,
    ) -> Notification:
        """
        Fetch a single notification by ID within a tenant.

        Enforces tenant isolation: even if the caller guesses the correct
        UUID, they cannot retrieve a notification from another tenant.

        Raises:
            NotFoundError  if the ID does not exist within this tenant.
        """
        notification = (
            self._db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,  # isolation guaranteed
            )
            .first()
        )
        if notification is None:
            raise NotFoundError("Notification", notification_id)
        return notification

    # ------------------------------------------------------------------
    # 4. count_unread
    # ------------------------------------------------------------------

    def count_unread(
        self,
        tenant_id: str,
        user_id: str | None,
    ) -> int:
        """
        Count unread notifications visible to (tenant_id, user_id).

        Used by the notification bell badge.
        """
        return (
            self._db.query(Notification)
            .filter(
                self._visibility_filter(tenant_id, user_id),
                Notification.read.is_(False),
            )
            .count()
        )

    # ------------------------------------------------------------------
    # 5. mark_read
    # ------------------------------------------------------------------

    def mark_read(
        self,
        notification_id: str,
        tenant_id: str,
        user_id: str | None,
    ) -> Notification:
        """
        Mark a single notification as read.

        Enforces both tenant isolation and visibility:
        - The notification must belong to tenant_id.
        - The notification must be visible to user_id (either tenant-wide
          or targeted at this specific user).

        This prevents a user from marking another user's private
        notification as read, even within the same tenant.

        Raises:
            NotFoundError  if not found within this tenant.
            ForbiddenError if the notification exists but is not visible
                           to the requesting user.
        """
        # Step 1: confirm the notification exists in this tenant
        notification = self.find_by_id(notification_id, tenant_id)

        # Step 2: confirm visibility for this specific user
        is_tenant_wide = notification.user_id is None
        is_targeted_at_user = notification.user_id == user_id

        if not is_tenant_wide and not is_targeted_at_user:
            raise ForbiddenError(
                "You do not have permission to mark this notification as read."
            )

        if not notification.read:
            notification.read = True
            notification.read_at = datetime.now(timezone.utc)
            self._db.commit()
            self._db.refresh(notification)

        return notification

    # ------------------------------------------------------------------
    # 6. mark_all_read
    # ------------------------------------------------------------------

    def mark_all_read(
        self,
        tenant_id: str,
        user_id: str | None,
    ) -> int:
        """
        Mark all visible unread notifications as read in a single query.

        Returns:
            The number of notifications updated.
        """
        now = datetime.now(timezone.utc)

        updated_count: int = (
            self._db.query(Notification)
            .filter(
                self._visibility_filter(tenant_id, user_id),
                Notification.read.is_(False),
            )
            .update(
                {"read": True, "read_at": now},
                synchronize_session="fetch",
            )
        )
        self._db.commit()
        return updated_count
