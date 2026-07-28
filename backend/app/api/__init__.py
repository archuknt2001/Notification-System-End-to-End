"""
API package.

Assembles all versioned routers into a single top-level router
that main.py mounts once under /api/v1.

Adding a new resource = create app/api/v1/<resource>.py
and include its router below. main.py stays unchanged.
"""

from fastapi import APIRouter

from app.api.v1.notifications import router as notifications_router
from app.api.v1.events import router as events_router

api_router = APIRouter()
api_router.include_router(notifications_router)
api_router.include_router(events_router)

__all__ = ["api_router"]
