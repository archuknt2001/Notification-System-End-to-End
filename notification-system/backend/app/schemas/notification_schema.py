"""
Pydantic schemas for the Notification domain.

Separation of concerns:
  NotificationCreate  — inbound payload for POST /notifications
  NotificationRead    — outbound representation of a single notification
  NotificationList    — paginated list response data block
  UnreadCountRead     — response for GET /notifications/unread-count

All datetime fields are serialised as ISO-8601 strings so the frontend
can parse them with a single Date constructor.

The NOTIFICATION_TYPES set is the canonical list of allowed type values.
Validation is enforced here rather than at the database level so that
new types can be added without a migration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Allowed notification types (spec + brain.md)
# ---------------------------------------------------------------------------

NOTIFICATION_TYPES = frozenset(
    {
        "member_invited",
        "new_reply",
        "report_ready",
        "campaign_started",
        "campaign_completed",
        "payment_received",
        "invoice_due",
        "warning",
        "success",
        "system_alert",
        "error",
    }
)

NotificationType = Literal[
    "member_invited",
    "new_reply",
    "report_ready",
    "campaign_started",
    "campaign_completed",
    "payment_received",
    "invoice_due",
    "warning",
    "success",
    "system_alert",
    "error",
]


# ---------------------------------------------------------------------------
# Inbound schemas
# ---------------------------------------------------------------------------


class NotificationCreate(BaseModel):
    """
    Payload for POST /notifications.

    tenant_id and user_id are NOT accepted here — they come from the
    TenantContext (request headers) to prevent spoofing.

    Fields:
        type     : one of the allowed NOTIFICATION_TYPES
        title    : short human-readable summary (max 255 chars)
        body     : full notification message
        user_id  : optional target user; None = tenant-wide broadcast
    """

    type: NotificationType = Field(
        ...,
        description="Notification type. Must be one of the allowed types.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Short notification title.",
    )
    body: str = Field(
        ...,
        min_length=1,
        description="Full notification body text.",
    )
    user_id: str | None = Field(
        default=None,
        description=(
            "Target user ID. Leave null to broadcast to the entire tenant."
        ),
    )

    @field_validator("title", "body", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Outbound schemas
# ---------------------------------------------------------------------------


class NotificationRead(BaseModel):
    """
    Single notification in API responses.

    Maps 1-to-1 to the ORM model; timestamps serialised as ISO-8601.
    """

    model_config = {"from_attributes": True}

    id: str
    tenant_id: str
    user_id: str | None
    type: str
    title: str
    body: str
    read: bool
    created_at: datetime
    read_at: datetime | None

    @classmethod
    def from_orm_model(cls, obj) -> "NotificationRead":
        """Convenience factory — keeps controllers clean."""
        return cls.model_validate(obj)


class NotificationList(BaseModel):
    """
    Paginated list response — the `data` block of a list endpoint.

    items       : the current page of notifications
    total       : total matching records across all pages
    page        : current page (1-based)
    size        : page size used for this request
    total_pages : total number of pages
    has_next    : whether a next page exists
    has_prev    : whether a previous page exists
    """

    items: list[NotificationRead]
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UnreadCountRead(BaseModel):
    """Response for GET /notifications/unread-count."""

    unread_count: int
