"""
Event API endpoints.

These endpoints simulate business events triggering notifications.
Controllers NEVER create notifications directly — they call EventService,
which calls NotificationService, which calls the Repository.

Routes:
    POST /events/member-invited     Fire a member_invited event (tenant-wide)
    POST /events/creator-reply      Fire a new_reply event (user-specific)
    POST /events/campaign-started   Fire a campaign_started event (tenant-wide)
    POST /events/campaign-completed Fire a campaign_completed event (tenant-wide)
    POST /events/payment-received   Fire a payment_received event (user-specific)
    POST /events/report-ready       Fire a report_ready event (user-specific)
    POST /events/invoice-due        Fire an invoice_due event (user-specific)
    POST /events/system-alert       Fire a system_alert event (tenant-wide or user)
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database.session import get_db
from app.middleware.context import TenantContext, get_tenant_context
from app.services.event_service import EventService

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(db)


# ---------------------------------------------------------------------------
# Request schemas — one per event, only business context fields
# ---------------------------------------------------------------------------

class MemberInvitedEvent(BaseModel):
    invited_by: str = Field(..., description="Display name of the user sending the invite.")
    invitee_name: str = Field(..., description="Name of the person being invited.")
    invitee_email: str = Field(..., description="Email of the person being invited.")


class CreatorReplyEvent(BaseModel):
    recipient_user_id: str = Field(..., description="User ID of the message recipient.")
    creator_handle: str = Field(..., description="@ handle of the creator who replied.")
    preview: str = Field(..., description="Preview text of the reply (truncated to 120 chars).")


class CampaignEvent(BaseModel):
    campaign_name: str = Field(..., description="Name of the campaign.")


class PaymentReceivedEvent(BaseModel):
    recipient_user_id: str = Field(..., description="User ID of the payment recipient.")
    amount: str = Field(..., description="Payment amount as a display string e.g. '$4,500'.")
    source: str = Field(..., description="Name of the payer or source.")


class ReportReadyEvent(BaseModel):
    recipient_user_id: str = Field(..., description="User ID of the report requester.")
    report_name: str = Field(..., description="Human-readable report name.")


class InvoiceDueEvent(BaseModel):
    recipient_user_id: str = Field(..., description="User ID of the finance contact.")
    invoice_number: str = Field(..., description="Invoice reference number.")
    amount: str = Field(..., description="Invoice amount as a display string.")
    due_in_days: int = Field(..., description="Days until due. 0 or negative = overdue.")


class SystemAlertEvent(BaseModel):
    title: str = Field(..., description="Alert title.")
    message: str = Field(..., description="Alert body text.")
    user_id: str | None = Field(
        default=None,
        description="Target user ID. Leave null for a tenant-wide alert.",
    )


# ---------------------------------------------------------------------------
# POST /events/member-invited  — tenant-wide notification
# ---------------------------------------------------------------------------

@router.post(
    "/member-invited",
    status_code=201,
    summary="Fire: member invited",
    description=(
        "Simulates a member invitation business event. "
        "Creates a tenant-wide notification visible to all users in the tenant."
    ),
)
def fire_member_invited(
    payload: MemberInvitedEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.member_invited(
        tenant_id=ctx.tenant_id,
        invited_by=payload.invited_by,
        invitee_name=payload.invitee_name,
        invitee_email=payload.invitee_email,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="member_invited event fired. Tenant-wide notification created.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/creator-reply  — user-specific notification
# ---------------------------------------------------------------------------

@router.post(
    "/creator-reply",
    status_code=201,
    summary="Fire: creator reply",
    description=(
        "Simulates a creator replying to a user's message. "
        "Creates a user-specific notification visible only to the recipient."
    ),
)
def fire_creator_reply(
    payload: CreatorReplyEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.creator_reply(
        tenant_id=ctx.tenant_id,
        recipient_user_id=payload.recipient_user_id,
        creator_handle=payload.creator_handle,
        preview=payload.preview,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="creator_reply event fired. User notification created.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/campaign-started  — tenant-wide
# ---------------------------------------------------------------------------

@router.post(
    "/campaign-started",
    status_code=201,
    summary="Fire: campaign started",
)
def fire_campaign_started(
    payload: CampaignEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.campaign_started(
        tenant_id=ctx.tenant_id,
        campaign_name=payload.campaign_name,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="campaign_started event fired.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/campaign-completed  — tenant-wide
# ---------------------------------------------------------------------------

@router.post(
    "/campaign-completed",
    status_code=201,
    summary="Fire: campaign completed",
)
def fire_campaign_completed(
    payload: CampaignEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.campaign_completed(
        tenant_id=ctx.tenant_id,
        campaign_name=payload.campaign_name,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="campaign_completed event fired.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/payment-received  — user-specific
# ---------------------------------------------------------------------------

@router.post(
    "/payment-received",
    status_code=201,
    summary="Fire: payment received",
)
def fire_payment_received(
    payload: PaymentReceivedEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.payment_received(
        tenant_id=ctx.tenant_id,
        recipient_user_id=payload.recipient_user_id,
        amount=payload.amount,
        source=payload.source,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="payment_received event fired.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/report-ready  — user-specific
# ---------------------------------------------------------------------------

@router.post(
    "/report-ready",
    status_code=201,
    summary="Fire: report ready",
)
def fire_report_ready(
    payload: ReportReadyEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.report_ready(
        tenant_id=ctx.tenant_id,
        recipient_user_id=payload.recipient_user_id,
        report_name=payload.report_name,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="report_ready event fired.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/invoice-due  — user-specific
# ---------------------------------------------------------------------------

@router.post(
    "/invoice-due",
    status_code=201,
    summary="Fire: invoice due",
)
def fire_invoice_due(
    payload: InvoiceDueEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.invoice_due(
        tenant_id=ctx.tenant_id,
        recipient_user_id=payload.recipient_user_id,
        invoice_number=payload.invoice_number,
        amount=payload.amount,
        due_in_days=payload.due_in_days,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="invoice_due event fired.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /events/system-alert  — tenant-wide or user-specific
# ---------------------------------------------------------------------------

@router.post(
    "/system-alert",
    status_code=201,
    summary="Fire: system alert",
    description=(
        "Fires a system alert. Leave user_id null for a tenant-wide alert, "
        "or set it to target a specific user."
    ),
)
def fire_system_alert(
    payload: SystemAlertEvent,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: EventService = Depends(get_event_service),
):
    notification = svc.system_alert(
        tenant_id=ctx.tenant_id,
        title=payload.title,
        message=payload.message,
        user_id=payload.user_id,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="system_alert event fired.",
        status_code=201,
    )
