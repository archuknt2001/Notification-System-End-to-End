"""
Tenant and user context extraction.

Current implementation: reads X-Tenant-Id and X-User-Id from request headers.
These are treated as trusted identity for this challenge.

Future JWT migration path:
  1. Replace get_tenant_context body to decode a Bearer token.
  2. Extract tenant_id and user_id from the token claims.
  3. TenantContext, its usage in routes, and all downstream layers
     remain completely unchanged.

Design rules:
  - tenant_id is REQUIRED. Missing → 401 Unauthorized.
  - user_id is OPTIONAL. None means the request acts as a tenant-level
    caller (useful for admin/system operations).
  - Routes never access request.headers directly; they always declare
    the dependency and receive a TenantContext.
  - Service and Repository layers only receive tenant_id / user_id as
    plain strings — they have zero knowledge of HTTP headers.
"""

from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.exceptions import HTTPException


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable request-scoped identity.

    tenant_id : str        — the owning tenant for this request.
    user_id   : str | None — the authenticated user, or None for
                             tenant-level / system callers.
    """

    tenant_id: str
    user_id: str | None


def get_tenant_context(
    x_tenant_id: str = Header(
        ...,
        alias="X-Tenant-Id",
        description="Required. Identifies the tenant for this request.",
    ),
    x_user_id: str | None = Header(
        default=None,
        alias="X-User-Id",
        description="Optional. Identifies the authenticated user within the tenant.",
    ),
) -> TenantContext:
    """
    FastAPI dependency — resolves on every request that declares it.

    Raises:
        HTTP 401  if X-Tenant-Id header is missing or blank.
        HTTP 422  (FastAPI default) if the header type is invalid.

    Usage in a route:
        @router.get("/notifications")
        def list_notifications(ctx: TenantContext = Depends(get_tenant_context)):
            ...
    """
    # FastAPI enforces the `...` (required) constraint on x_tenant_id,
    # but we add an explicit blank-string guard for extra safety.
    if not x_tenant_id or not x_tenant_id.strip():
        raise HTTPException(
            status_code=401,
            detail="X-Tenant-Id header is required.",
        )

    # Strip surrounding whitespace so callers cannot sneak in padding.
    tenant_id = x_tenant_id.strip()
    user_id = x_user_id.strip() if x_user_id else None

    return TenantContext(tenant_id=tenant_id, user_id=user_id)
