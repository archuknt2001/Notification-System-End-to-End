"""
EventService — maps business events to notifications.

Rules (from the spec):
  - Controllers NEVER create notifications directly.
  - Controllers call EventService methods.
  - EventService calls NotificationService.
  - NotificationService calls the Repository.
  - The event system must be reusable and extensible.

Design:
  Each public method represents one named business event.
  Adding a new business event = adding one method here.
  The notification payload (type, title, body, targeting) is
  determined entirely inside this class — callers only supply
  the business context (who, what happened).

Required demo events (from the spec):
  member_invited  → tenant-wide notification
  creator_reply   → user-specific notification

Additional events are included for completeness and to demonstrate
the reusability pattern.
"""

from sqlalchemy.orm import Session

from app.schemas.notification_schema import NotificationCreate, NotificationRead
from app.services.notification_service import NotificationService


class EventService:
    """
    Translates domain events into notifications.

    Instantiated per-request, receiving the DB session via dependency
    injection from the route handler.
    """

    def __init__(self, db: Session) -> None:
        self._notification_svc = NotificationService(db)

    # ------------------------------------------------------------------
    # Demo Event 1 — member_invited (tenant-wide)
    # Spec: "Invite Team Member → Create Tenant-wide Notification"
    # ------------------------------------------------------------------

    def member_invited(
        self,
        tenant_id: str,
        invited_by: str,
        invitee_name: str,
        invitee_email: str,
    ) -> NotificationRead:
        """
        Fired when a new member is invited to the tenant.

        Creates a TENANT-WIDE notification (user_id=None) so every user
        in the tenant sees it in their notification list.

        Args:
            tenant_id     : owning tenant.
            invited_by    : display name of the user who sent the invite.
            invitee_name  : name of the person being invited.
            invitee_email : email of the person being invited.
        """
        payload = NotificationCreate(
            type="member_invited",
            title=f"New member invited: {invitee_name}",
            body=(
                f"{invited_by} has invited {invitee_name} ({invitee_email}) "
                f"to join the team."
            ),
            user_id=None,  # tenant-wide broadcast
        )
        return self._notification_svc.create(
            tenant_id=tenant_id,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Demo Event 2 — creator_reply (user-specific)
    # Spec: "Creator Reply → Create User Notification"
    # ------------------------------------------------------------------

    def creator_reply(
        self,
        tenant_id: str,
        recipient_user_id: str,
        creator_handle: str,
        preview: str,
    ) -> NotificationRead:
        """
        Fired when a creator replies to a message from a specific user.

        Creates a USER-SPECIFIC notification so only the recipient sees it.

        Args:
            tenant_id          : owning tenant.
            recipient_user_id  : the user who sent the original message.
            creator_handle     : @ handle of the creator who replied.
            preview            : short preview of the reply text.
        """
        # Truncate preview to keep the notification body readable
        preview_text = preview[:120] + "..." if len(preview) > 120 else preview

        payload = NotificationCreate(
            type="new_reply",
            title=f"{creator_handle} replied to your message",
            body=f'{creator_handle} replied: "{preview_text}"',
            user_id=recipient_user_id,  # user-specific
        )
        return self._notification_svc.create(
            tenant_id=tenant_id,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Additional reusable events
    # ------------------------------------------------------------------

    def campaign_started(
        self,
        tenant_id: str,
        campaign_name: str,
    ) -> NotificationRead:
        """Tenant-wide alert when a campaign goes live."""
        payload = NotificationCreate(
            type="campaign_started",
            title=f"Campaign launched: {campaign_name}",
            body=f"The '{campaign_name}' campaign has officially started.",
            user_id=None,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)

    def campaign_completed(
        self,
        tenant_id: str,
        campaign_name: str,
    ) -> NotificationRead:
        """Tenant-wide alert when a campaign finishes."""
        payload = NotificationCreate(
            type="campaign_completed",
            title=f"Campaign completed: {campaign_name}",
            body=f"The '{campaign_name}' campaign has been completed successfully.",
            user_id=None,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)

    def payment_received(
        self,
        tenant_id: str,
        recipient_user_id: str,
        amount: str,
        source: str,
    ) -> NotificationRead:
        """User-specific alert for an incoming payment."""
        payload = NotificationCreate(
            type="payment_received",
            title="Payment received",
            body=f"A payment of {amount} has been received from {source}.",
            user_id=recipient_user_id,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)

    def invoice_due(
        self,
        tenant_id: str,
        recipient_user_id: str,
        invoice_number: str,
        amount: str,
        due_in_days: int,
    ) -> NotificationRead:
        """User-specific invoice due reminder."""
        if due_in_days <= 0:
            urgency = "is now overdue"
        elif due_in_days == 1:
            urgency = "is due tomorrow"
        else:
            urgency = f"is due in {due_in_days} days"

        payload = NotificationCreate(
            type="invoice_due",
            title=f"Invoice {urgency}: {invoice_number}",
            body=f"Invoice {invoice_number} for {amount} {urgency}. Please follow up.",
            user_id=recipient_user_id,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)

    def report_ready(
        self,
        tenant_id: str,
        recipient_user_id: str,
        report_name: str,
    ) -> NotificationRead:
        """User-specific alert when a report has been generated."""
        payload = NotificationCreate(
            type="report_ready",
            title=f"Report ready: {report_name}",
            body=f"Your report '{report_name}' has been generated and is ready to download.",
            user_id=recipient_user_id,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)

    def system_alert(
        self,
        tenant_id: str,
        title: str,
        message: str,
        user_id: str | None = None,
    ) -> NotificationRead:
        """
        Flexible system alert — tenant-wide by default, or targeted
        at a specific user if user_id is provided.
        """
        payload = NotificationCreate(
            type="system_alert",
            title=title,
            body=message,
            user_id=user_id,
        )
        return self._notification_svc.create(tenant_id=tenant_id, payload=payload)
