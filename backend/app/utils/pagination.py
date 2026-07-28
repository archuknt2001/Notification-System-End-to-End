"""
Pagination helpers shared across service and schema layers.

PaginationParams is injected as a FastAPI dependency so every
list endpoint gets consistent page/size handling without
duplicating validation logic.

Usage in a route:
    @router.get("/notifications")
    def list_notifications(pagination: PaginationParams = Depends()):
        ...
"""

from dataclasses import dataclass
from fastapi import Query

from app.core.config import settings


@dataclass
class PaginationParams:
    """
    Dependency-injectable pagination parameters.

    page  : 1-based page number (default 1)
    size  : items per page (default from settings, capped at max_page_size)
    """

    page: int = Query(default=1, ge=1, description="Page number (1-based)")
    size: int = Query(
        default=settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Items per page",
    )

    @property
    def offset(self) -> int:
        """SQL OFFSET derived from page and size."""
        return (self.page - 1) * self.size


def build_pagination_meta(
    total: int,
    page: int,
    size: int,
) -> dict:
    """
    Build the `meta` block returned in every paginated response.

    Returns:
        {
            "total":        int   — total matching records,
            "page":         int   — current page (1-based),
            "size":         int   — page size requested,
            "total_pages":  int   — total number of pages,
            "has_next":     bool  — whether a next page exists,
            "has_prev":     bool  — whether a previous page exists,
        }
    """
    import math

    total_pages = max(1, math.ceil(total / size)) if size > 0 else 1
    return {
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
