"""
Notification API endpoints.

Routes:
    POST   /notifications                   Create a notification
    GET    /notifications                   List visible notifications (paginated)
    GET    /notifications/unread-count      Unread badge count
    PATCH  /notifications/{id}/read         Mark one notification read
    PATCH  /notifications/read-all          Mark all visible notifications read

Design rules:
    - Routes never access the database directly.
    - Routes never instantiate the repository.
    - Routes call NotificationService only.
    - TenantContext is resolved by the get_tenant_context dependency.
    - All responses use the standard success_response / error_response envelope.
    - The /unread-count route is declared BEFORE /{id}/read so FastAPI
      doesn't misinterpret "unread-count" as a notification ID.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database.session import get_db
from app.middleware.context import TenantContext, get_tenant_context
from app.schemas.notification_schema import NotificationCreate
from app.services.notification_service import NotificationService
from app.utils.pagination import PaginationParams, build_pagination_meta

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


# ---------------------------------------------------------------------------
# Dependency helpers — keep route signatures clean
# ---------------------------------------------------------------------------

def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    """Inject a per-request NotificationService instance."""
    return NotificationService(db)


# ---------------------------------------------------------------------------
# POST /notifications — Create a notification
# ---------------------------------------------------------------------------

@router.post(
    "",
    status_code=201,
    summary="Create a notification",
    description=(
        "Creates a new notification for the current tenant. "
        "Set `user_id` in the body to target a specific user, or leave it "
        "null to broadcast to the entire tenant."
    ),
)
def create_notification(
    payload: NotificationCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: NotificationService = Depends(get_notification_service),
):
    notification = svc.create(tenant_id=ctx.tenant_id, payload=payload)
    return success_response(
        data=notification.model_dump(mode="json"),
        message="Notification created.",
        status_code=201,
    )


# ---------------------------------------------------------------------------
# GET /notifications/unread-count — Unread badge count
# IMPORTANT: declared before /{id}/read to avoid route collision
# ---------------------------------------------------------------------------

@router.get(
    "/unread-count",
    summary="Get unread notification count",
    description=(
        "Returns the count of unread notifications visible to the current "
        "user. Used to populate the notification bell badge."
    ),
)
def get_unread_count(
    ctx: TenantContext = Depends(get_tenant_context),
    svc: NotificationService = Depends(get_notification_service),
):
    result = svc.get_unread_count(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
    )
    return success_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# GET /notifications — List visible notifications (paginated)
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="List notifications",
    description=(
        "Returns a paginated list of notifications visible to the current user. "
        "Ordering: unread first, then newest first within each group."
    ),
)
def list_notifications(
    pagination: PaginationParams = Depends(),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: NotificationService = Depends(get_notification_service),
):
    result = svc.list_notifications(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        page=pagination.page,
        size=pagination.size,
    )

    items = [n.model_dump(mode="json") for n in result.items]
    meta = build_pagination_meta(
        total=result.total,
        page=result.page,
        size=result.size,
    )

    return success_response(data=items, meta=meta)


# ---------------------------------------------------------------------------
# PATCH /notifications/read-all — Mark all visible notifications read
# IMPORTANT: declared before /{id}/read to avoid route collision
# ---------------------------------------------------------------------------

@router.patch(
    "/read-all",
    summary="Mark all notifications as read",
    description=(
        "Marks all unread notifications visible to the current user as read "
        "in a single operation."
    ),
)
def mark_all_read(
    ctx: TenantContext = Depends(get_tenant_context),
    svc: NotificationService = Depends(get_notification_service),
):
    result = svc.mark_all_read(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
    )
    return success_response(
        data=result,
        message=f"{result['updated']} notification(s) marked as read.",
    )


# ---------------------------------------------------------------------------
# PATCH /notifications/{id}/read — Mark one notification read
# ---------------------------------------------------------------------------

@router.patch(
    "/{notification_id}/read",
    summary="Mark a notification as read",
    description=(
        "Marks a single notification as read. "
        "Returns 404 if the notification does not exist within the current tenant. "
        "Returns 403 if the notification exists but is not visible to the current user."
    ),
)
def mark_read(
    notification_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: NotificationService = Depends(get_notification_service),
):
    notification = svc.mark_read(
        notification_id=notification_id,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
    )
    return success_response(
        data=notification.model_dump(mode="json"),
        message="Notification marked as read.",
    )
