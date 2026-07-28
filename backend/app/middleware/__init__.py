"""
Middleware / context package.

Re-exports the public surface so consumers import from `app.middleware`
rather than from the concrete module path.
"""

from app.middleware.context import TenantContext, get_tenant_context  # noqa: F401

__all__ = ["TenantContext", "get_tenant_context"]
