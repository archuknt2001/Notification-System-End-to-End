"""
Seed script — demo data for the AI-Native CRM Notification System.

Creates two tenants with two users each, covering all 11 notification
types defined in the spec. Mix of:
  - Tenant-wide notifications (user_id = NULL)
  - User-specific notifications (user_id set)
  - Read and unread states
  - Various created_at offsets to demonstrate sorting

Usage:
    python seed.py              # seeds only if DB is empty
    python seed.py --force      # drops and re-seeds regardless
"""

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.models.notification import Notification

# ---------------------------------------------------------------------------
# Fixed UUIDs — stable across re-runs so frontend/API demos are repeatable
# ---------------------------------------------------------------------------

# Tenant A — "Stellar Talent Agency"
TENANT_A = "tenant-stellar-0001"
USER_A1 = "user-alice-00000001"   # Alice — account manager
USER_A2 = "user-bob-000000001"    # Bob — campaign lead

# Tenant B — "Nova Influencer Co"
TENANT_B = "tenant-nova-00001"
USER_B1 = "user-carol-0000001"   # Carol — talent scout
USER_B2 = "user-dave-00000001"   # Dave — finance lead


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ago(minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    return _utcnow() - timedelta(minutes=minutes, hours=hours, days=days)


def _nid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Seed payload
# ---------------------------------------------------------------------------

def build_seed_data() -> list[dict]:
    """
    Returns a list of dicts ready to pass to Notification(**row).
    Organised by tenant so it is easy to read and extend.
    """
    rows: list[dict] = []

    # -----------------------------------------------------------------------
    # TENANT A — Stellar Talent Agency
    # -----------------------------------------------------------------------

    # 1. Tenant-wide: a new member was invited to the agency (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=None,
        type="member_invited",
        title="New member invited",
        body="Sarah Connor has been invited to join Stellar Talent Agency.",
        read=False, created_at=_ago(minutes=5),
    ))

    # 2. Tenant-wide: a campaign just started (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=None,
        type="campaign_started",
        title="Campaign launched",
        body="The 'Summer Glow' campaign has officially started.",
        read=False, created_at=_ago(minutes=30),
    ))

    # 3. Tenant-wide: campaign completed (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=None,
        type="campaign_completed",
        title="Campaign completed",
        body="The 'Spring Bloom' influencer campaign has been completed successfully.",
        read=True, read_at=_ago(hours=1), created_at=_ago(hours=2),
    ))

    # 4. Tenant-wide: system alert (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=None,
        type="system_alert",
        title="Scheduled maintenance",
        body="The platform will be offline for maintenance on Sunday 2am–4am UTC.",
        read=False, created_at=_ago(hours=3),
    ))

    # 5. User A1 (Alice) specific: a creator replied to her message (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A1,
        type="new_reply",
        title="Creator replied",
        body="@maya_creates replied to your message: 'Sounds great, let's schedule a call!'",
        read=False, created_at=_ago(minutes=10),
    ))

    # 6. User A1 (Alice) specific: report is ready (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A1,
        type="report_ready",
        title="Your report is ready",
        body="The Q2 talent performance report has been generated and is ready to download.",
        read=False, created_at=_ago(hours=1),
    ))

    # 7. User A1 (Alice) specific: success notification (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A1,
        type="success",
        title="Contract signed",
        body="The contract with @influencer_jay has been signed successfully.",
        read=True, read_at=_ago(days=1), created_at=_ago(days=1, hours=2),
    ))

    # 8. User A2 (Bob) specific: payment received (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A2,
        type="payment_received",
        title="Payment received",
        body="A payment of $4,500 has been received for the 'Glow Up' campaign.",
        read=False, created_at=_ago(hours=4),
    ))

    # 9. User A2 (Bob) specific: invoice due warning (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A2,
        type="invoice_due",
        title="Invoice due soon",
        body="Invoice #INV-2024-089 for $2,200 is due in 3 days.",
        read=False, created_at=_ago(hours=6),
    ))

    # 10. User A2 (Bob) specific: warning (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_A, user_id=USER_A2,
        type="warning",
        title="Budget threshold reached",
        body="The 'Summer Glow' campaign has consumed 80% of its allocated budget.",
        read=True, read_at=_ago(days=2), created_at=_ago(days=2, hours=1),
    ))

    # -----------------------------------------------------------------------
    # TENANT B — Nova Influencer Co
    # Demonstrates strict tenant isolation — none of these should ever
    # appear when querying as Tenant A users.
    # -----------------------------------------------------------------------

    # 11. Tenant-wide: member invited (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=None,
        type="member_invited",
        title="New member invited",
        body="James Rivera has been invited to join Nova Influencer Co.",
        read=False, created_at=_ago(minutes=15),
    ))

    # 12. Tenant-wide: system alert (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=None,
        type="system_alert",
        title="New feature available",
        body="AI-powered talent matching is now available for all campaigns.",
        read=False, created_at=_ago(hours=2),
    ))

    # 13. Tenant-wide: campaign started (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=None,
        type="campaign_started",
        title="Campaign launched",
        body="The 'Autumn Vibes' creator campaign has officially started.",
        read=True, read_at=_ago(days=1), created_at=_ago(days=1, hours=3),
    ))

    # 14. User B1 (Carol) specific: new reply (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B1,
        type="new_reply",
        title="Creator replied",
        body="@the_real_lena replied: 'I'm in! Send me the brief.'",
        read=False, created_at=_ago(minutes=45),
    ))

    # 15. User B1 (Carol) specific: report ready (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B1,
        type="report_ready",
        title="Campaign analytics ready",
        body="Your Q3 campaign performance report is ready for review.",
        read=False, created_at=_ago(hours=5),
    ))

    # 16. User B1 (Carol) specific: success (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B1,
        type="success",
        title="Talent onboarded",
        body="@nova_style has completed onboarding and is ready for campaigns.",
        read=True, read_at=_ago(days=3), created_at=_ago(days=3, hours=1),
    ))

    # 17. User B2 (Dave) specific: payment received (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B2,
        type="payment_received",
        title="Payment received",
        body="A payment of $7,800 has been received from BrandX for campaign delivery.",
        read=False, created_at=_ago(hours=8),
    ))

    # 18. User B2 (Dave) specific: invoice due (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B2,
        type="invoice_due",
        title="Invoice overdue",
        body="Invoice #INV-2024-112 for $1,500 is now overdue. Please follow up.",
        read=False, created_at=_ago(days=1, hours=2),
    ))

    # 19. Tenant B: campaign completed (unread)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=None,
        type="campaign_completed",
        title="Campaign completed",
        body="The 'City Pulse' creator campaign has been successfully completed.",
        read=False, created_at=_ago(days=2),
    ))

    # 20. User B2 (Dave) specific: warning (read)
    rows.append(dict(
        id=_nid(), tenant_id=TENANT_B, user_id=USER_B2,
        type="warning",
        title="Unusual activity detected",
        body="Multiple login attempts detected on your account. Please review security settings.",
        read=True, read_at=_ago(days=4), created_at=_ago(days=4, hours=2),
    ))

    return rows


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

def seed(force: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        existing_count = db.query(Notification).count()

        if existing_count > 0 and not force:
            print(
                f"[seed] Database already has {existing_count} notifications. "
                "Skipping. Run with --force to re-seed."
            )
            return

        if force and existing_count > 0:
            deleted = db.query(Notification).delete()
            db.commit()
            print(f"[seed] Cleared {deleted} existing notifications.")

        rows = build_seed_data()
        notifications = [Notification(**row) for row in rows]
        db.add_all(notifications)
        db.commit()

        print(f"[seed] Inserted {len(notifications)} notifications.")
        print(f"       Tenant A ({TENANT_A}): {sum(1 for r in rows if r['tenant_id'] == TENANT_A)} rows")
        print(f"       Tenant B ({TENANT_B}): {sum(1 for r in rows if r['tenant_id'] == TENANT_B)} rows")
        print(f"       Tenant-wide (user_id=NULL): {sum(1 for r in rows if r['user_id'] is None)} rows")
        print(f"       User-specific: {sum(1 for r in rows if r['user_id'] is not None)} rows")
        print(f"       Unread: {sum(1 for r in rows if not r['read'])} rows")
        print(f"       Read:   {sum(1 for r in rows if r['read'])} rows")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop existing notifications and re-seed",
    )
    args = parser.parse_args()

    # Ensure tables exist (idempotent in dev; Alembic handles prod)
    Base.metadata.create_all(bind=engine)

    seed(force=args.force)
    sys.exit(0)
