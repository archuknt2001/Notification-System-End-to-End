"""
Domain exceptions used across all layers.

Raise these from Service/Repository; catch them in API handlers.
Never raise HTTPException from the service or repository layer.
"""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", resource_id: str | None = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} '{resource_id}' not found"
        super().__init__(detail)
        self.detail = detail


class ForbiddenError(Exception):
    """Raised when a tenant/user attempts to access another tenant's data."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(detail)
        self.detail = detail


class ValidationError(Exception):
    """Raised when business-rule validation fails."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail
