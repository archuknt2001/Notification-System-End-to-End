"""
Notification ORM model.

Design decisions:
- tenant_id  : required — every notification belongs to exactly one tenant.
- user_id    : nullable — NULL means the notification is tenant-wide (visible
               to every user in the tenant). A non-NULL value restricts
               visibility to that specific user.
- type       : plain string column; validated at the schema/service layer so
               new types can be added without a migration.
- read       : boolean with server-side default False — never NULL.
- read_at    : nullable datetime set when the notification is marked read.

Indexes:
- (tenant_id)              — all queries start with a tenant filter.
- (tenant_id, user_id)     — composite for the "visible to user" query.
- (tenant_id, read)        — unread-count query.
- (created_at)             — ordering; covered by the composite below.
- (tenant_id, read, created_at) — covers the primary list query fully.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    """Return current UTC time as an aware datetime."""
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # ------------------------------------------------------------------
    # Tenant / user targeting
    # ------------------------------------------------------------------
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        comment="Owning tenant — mandatory for all notifications.",
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="Target user. NULL = tenant-wide notification.",
    )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Notification type — e.g. member_invited, new_reply.",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="False = unread, True = read.",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        comment="UTC creation time.",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC time when the notification was marked read.",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Tenant filter — every query starts here
        Index("ix_notifications_tenant_id", "tenant_id"),
        # Visible-to-user query: WHERE tenant_id = ? AND (user_id = ? OR user_id IS NULL)
        Index("ix_notifications_tenant_user", "tenant_id", "user_id"),
        # Unread count: WHERE tenant_id = ? AND read = 0
        Index("ix_notifications_tenant_read", "tenant_id", "read"),
        # Full list query: ORDER BY read ASC, created_at DESC within tenant
        Index(
            "ix_notifications_tenant_read_created",
            "tenant_id",
            "read",
            "created_at",
        ),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id!r} tenant={self.tenant_id!r} "
            f"type={self.type!r} read={self.read}>"
        )
