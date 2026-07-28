"""
FastAPI application factory.

Responsibilities:
- Create and configure the FastAPI app instance.
- Register CORS middleware.
- Register global exception handlers that translate domain
  exceptions AND framework exceptions into a consistent
  { success, message, data, errors } envelope.
- Mount all API routers (added incrementally per phase).
- Run database table creation on startup (dev convenience;
  production uses Alembic migrations).

Authentication design:
- Phase 3 uses X-Tenant-Id / X-User-Id headers via the
  get_tenant_context dependency (app/middleware/context.py).
- To migrate to JWT later:
    1. Add a bearer-token middleware or update get_tenant_context.
    2. Nothing else in the stack changes.

Exception handler chain (outermost → innermost):
  RequestValidationError  → 422  (missing/invalid headers or body fields)
  HTTPException           → pass-through (FastAPI default + our envelope)
  NotFoundError           → 404
  ForbiddenError          → 403
  ValidationError         → 400  (domain-level business rule violation)
  Exception               → 500  (catch-all, detail hidden in production)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.responses import error_response
from app.database.base import Base
import app.database.session as _db_session_module


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: ensure all tables exist.
    Reads engine from the module at call-time so tests can swap it out.
    """
    Base.metadata.create_all(bind=_db_session_module.engine)
    yield


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Tenant-aware notification system for an AI-native CRM. "
            "Provides REST APIs for creating, listing, and managing notifications. "
            "All endpoints require the X-Tenant-Id header. "
            "X-User-Id is optional and scopes visibility to a specific user."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Exception handlers
    #
    # Rule: every handler returns the same envelope shape so the
    # frontend never has to inspect response structure conditionally.
    # ------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Catches missing/invalid request headers and body fields.
        FastAPI's default 422 response is replaced with our envelope.

        The `errors` field preserves the full pydantic error list so
        API consumers can see exactly which field failed.
        """
        errors = [
            {
                "field": " -> ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]

        # Surface a friendly top-level message for the most common case:
        # a missing required header (X-Tenant-Id).
        missing_headers = [
            e for e in errors if "header" in e["field"].lower()
        ]
        if missing_headers:
            message = "Missing required header: " + missing_headers[0]["field"]
        else:
            message = "Request validation failed."

        return error_response(message=message, status_code=422, errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Wraps all HTTPException instances (including those raised by
        get_tenant_context and FastAPI's own 404/405 handlers) in our
        standard envelope.
        """
        return error_response(message=str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        return error_response(message=exc.detail, status_code=404)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(
        request: Request, exc: ForbiddenError
    ) -> JSONResponse:
        return error_response(message=exc.detail, status_code=403)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return error_response(message=exc.detail, status_code=400)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Never expose internal detail in production
        message = str(exc) if settings.debug else "An unexpected error occurred."
        return error_response(message=message, status_code=500)

    # ------------------------------------------------------------------
    # Routers
    # All versioned routes are assembled in app/api/__init__.py and
    # mounted here under /api/v1. Adding a new resource requires
    # only a change in app/api/__init__.py — not here.
    # ------------------------------------------------------------------
    from app.api import api_router  # local import avoids circular deps at module load
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    def health_check():
        """Liveness probe. No authentication required."""
        return {"status": "ok", "version": settings.app_version}

    return app


# ---------------------------------------------------------------------------
# Module-level app instance consumed by uvicorn
# ---------------------------------------------------------------------------
app = create_app()
