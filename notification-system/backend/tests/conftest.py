"""
Test fixtures shared across all test modules.

Strategy:
- Each test function gets a fresh in-memory SQLite database.
  This guarantees full isolation — no test can affect another.
- The TestClient overrides the get_db dependency so all HTTP
  requests use the same in-memory session as the test assertions.
- Seeded fixtures create two tenants, two users each, covering
  all notification types.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.models.notification import Notification


# ---------------------------------------------------------------------------
# Fixed test identifiers
# ---------------------------------------------------------------------------

TENANT_A = "tenant-test-aaaa"
TENANT_B = "tenant-test-bbbb"
USER_A1  = "user-test-a1"
USER_A2  = "user-test-a2"
USER_B1  = "user-test-b1"
USER_B2  = "user-test-b2"

HDR_A1 = {"X-Tenant-Id": TENANT_A, "X-User-Id": USER_A1}
HDR_A2 = {"X-Tenant-Id": TENANT_A, "X-User-Id": USER_A2}
HDR_B1 = {"X-Tenant-Id": TENANT_B, "X-User-Id": USER_B1}
HDR_B2 = {"X-Tenant-Id": TENANT_B, "X-User-Id": USER_B2}
HDR_A_NO_USER = {"X-Tenant-Id": TENANT_A}


# ---------------------------------------------------------------------------
# Per-test in-memory database
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """
    Provide a fresh SQLAlchemy session backed by an in-memory SQLite DB.

    Critical: SQLite in-memory databases are per-connection. We create a
    single persistent connection and tell SQLAlchemy to always reuse it,
    so create_all and all queries share the same in-memory database.
    """
    from sqlalchemy import event
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # reuse the same connection — keeps in-memory DB alive
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient whose get_db dependency is overridden to use
    the per-test in-memory session (StaticPool — single shared connection).
    """
    import app.database.session as db_module
    from app.main import app as app_instance

    # Swap engine so lifespan's create_all runs on the test engine
    real_engine = db_module.engine
    db_module.engine = db_session.bind

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app_instance.dependency_overrides[get_db] = override_get_db

    with TestClient(app_instance, raise_server_exceptions=False) as c:
        yield c

    app_instance.dependency_overrides.clear()
    db_module.engine = real_engine


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _utcnow():
    return datetime.now(timezone.utc)


def _ago(**kwargs):
    return _utcnow() - timedelta(**kwargs)


def make_notification(db_session, **kwargs) -> Notification:
    """Create and persist a single notification with sensible defaults."""
    defaults = dict(
        tenant_id=TENANT_A,
        user_id=None,
        type="system_alert",
        title="Test notification",
        body="Test body",
        read=False,
        created_at=_utcnow(),
    )
    defaults.update(kwargs)
    n = Notification(**defaults)
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)
    return n


@pytest.fixture()
def seeded(db_session):
    """
    Returns a dict of pre-created notifications for both tenants.
    Covers all visibility combinations:
      - tenant-wide unread
      - tenant-wide read
      - user-specific unread (A1, A2, B1)
      - user-specific read (A1)
    """
    data = {}

    # TENANT A — tenant-wide notifications
    data["a_wide_unread_1"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=None, type="member_invited",
        title="Member invited", read=False, created_at=_ago(minutes=5))
    data["a_wide_unread_2"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=None, type="campaign_started",
        title="Campaign started", read=False, created_at=_ago(minutes=10))
    data["a_wide_read"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=None, type="system_alert",
        title="System alert (read)", read=True,
        read_at=_ago(hours=1), created_at=_ago(hours=2))

    # TENANT A — user A1 specific
    data["a1_unread_1"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=USER_A1, type="new_reply",
        title="Reply for A1", read=False, created_at=_ago(minutes=2))
    data["a1_unread_2"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=USER_A1, type="report_ready",
        title="Report for A1", read=False, created_at=_ago(minutes=8))
    data["a1_read"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=USER_A1, type="success",
        title="Success for A1 (read)", read=True,
        read_at=_ago(days=1), created_at=_ago(days=1, hours=2))

    # TENANT A — user A2 specific
    data["a2_unread"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=USER_A2, type="payment_received",
        title="Payment for A2", read=False, created_at=_ago(hours=1))
    data["a2_read"] = make_notification(db_session,
        tenant_id=TENANT_A, user_id=USER_A2, type="invoice_due",
        title="Invoice for A2 (read)", read=True,
        read_at=_ago(days=2), created_at=_ago(days=2, hours=1))

    # TENANT B — completely separate
    data["b_wide_unread"] = make_notification(db_session,
        tenant_id=TENANT_B, user_id=None, type="system_alert",
        title="B tenant-wide unread", read=False, created_at=_ago(minutes=3))
    data["b1_unread"] = make_notification(db_session,
        tenant_id=TENANT_B, user_id=USER_B1, type="new_reply",
        title="Reply for B1", read=False, created_at=_ago(minutes=1))

    return data
