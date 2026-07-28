# Database Schema

## Overview

The notification system uses a single table: `notifications`. All business rules are enforced at the application layer (repository + service); the database schema focuses on correctness, index coverage, and migration safety.

Migration tool: **Alembic**
Migration file: `alembic/versions/bb8819ae44fc_create_notifications_table.py`

---

## Table: notifications

```sql
CREATE TABLE notifications (
    id          VARCHAR(36)  NOT NULL,
    tenant_id   VARCHAR(36)  NOT NULL,
    user_id     VARCHAR(36),
    type        VARCHAR(50)  NOT NULL,
    title       VARCHAR(255) NOT NULL,
    body        TEXT         NOT NULL,
    read        BOOLEAN      NOT NULL DEFAULT '0',
    created_at  DATETIME     NOT NULL,
    read_at     DATETIME,
    PRIMARY KEY (id)
);
```

---

## Column Reference

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | VARCHAR(36) | No | — | UUID v4, generated in Python on insert |
| `tenant_id` | VARCHAR(36) | No | — | Owning tenant. Every query filters by this first. |
| `user_id` | VARCHAR(36) | Yes | NULL | Target user. NULL = visible to all users in tenant. |
| `type` | VARCHAR(50) | No | — | Notification type string. Validated at schema layer. |
| `title` | VARCHAR(255) | No | — | Short human-readable title. |
| `body` | TEXT | No | — | Full notification body text. |
| `read` | BOOLEAN | No | `0` (False) | False = unread, True = read. |
| `created_at` | DATETIME | No | — | UTC creation timestamp, set by application on insert. |
| `read_at` | DATETIME | Yes | NULL | UTC timestamp when notification was marked read. NULL if unread. |

---

## Indexes

Four indexes are defined to cover all query patterns efficiently.

### ix_notifications_tenant_id
```sql
CREATE INDEX ix_notifications_tenant_id ON notifications (tenant_id);
```
Used by: all queries that start with a tenant filter.

### ix_notifications_tenant_user
```sql
CREATE INDEX ix_notifications_tenant_user ON notifications (tenant_id, user_id);
```
Used by: visibility filter — `WHERE tenant_id = ? AND (user_id IS NULL OR user_id = ?)`.

### ix_notifications_tenant_read
```sql
CREATE INDEX ix_notifications_tenant_read ON notifications (tenant_id, read);
```
Used by: unread count query — `WHERE tenant_id = ? AND read = 0`.

### ix_notifications_tenant_read_created
```sql
CREATE INDEX ix_notifications_tenant_read_created ON notifications (tenant_id, read, created_at);
```
Used by: the primary list query — filter by tenant, order by `read ASC, created_at DESC`. This index covers the full query without a table scan.

---

## Business Rules (enforced at application layer)

### Visibility rule

A notification is visible to `(tenant_id, user_id)` when:

```
notification.tenant_id = caller.tenant_id
AND (
    notification.user_id IS NULL          -- tenant-wide: visible to everyone
    OR notification.user_id = caller.user_id  -- targeted: only for this user
)
```

A tenant-level caller (no `X-User-Id` header, `user_id = None`) sees **only** tenant-wide notifications (`user_id IS NULL`).

### Tenant isolation rule

Every query **must** include `WHERE tenant_id = ?`. This is enforced structurally in `NotificationRepository._visibility_filter`. There is no way to query across tenants from any higher layer.

### Read state rule

- `read` starts as `False` on all new notifications.
- `read` is set to `True` and `read_at` is set to the current UTC time when marked read.
- Marking an already-read notification is idempotent — no update is performed.

### Ordering rule

Lists are always returned: unread first (`read ASC`), then newest first within each group (`created_at DESC`).

---

## Allowed Notification Types

Validated at the Pydantic schema layer (`app/schemas/notification_schema.py`). Adding a new type requires only a schema change — no migration needed.

```python
NOTIFICATION_TYPES = {
    "member_invited",
    "new_reply",
    "report_ready",
    "campaign_started",
    "campaign_completed",
    "payment_received",
    "invoice_due",
    "warning",
    "success",
    "system_alert",
    "error",
}
```

---

## Migration History

| Revision | Description |
|---|---|
| `bb8819ae44fc` | Initial — creates `notifications` table with all columns and indexes |

### Running migrations

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Rollback one migration
python -m alembic downgrade -1

# Check current revision
python -m alembic current

# Generate a new migration from model changes
python -m alembic revision --autogenerate -m "description"
```

---

## Seed Data

`seed.py` creates 20 demo notifications across two tenants:

| Tenant | Rows | Unread | Read |
|---|---|---|---|
| `tenant-stellar-0001` (Stellar Talent Agency) | 10 | 7 | 3 |
| `tenant-nova-00001` (Nova Influencer Co) | 10 | 7 | 3 |

Users:
- **Stellar:** Alice (`user-alice-00000001`), Bob (`user-bob-000000001`)
- **Nova:** Carol (`user-carol-0000001`), Dave (`user-dave-00000001`)

Notification targeting:
- 8 tenant-wide (`user_id IS NULL`)
- 12 user-specific

All 11 notification types are represented.

---

## Future Schema Considerations

| Enhancement | Change Required |
|---|---|
| Soft delete | Add `deleted_at DATETIME NULL` column + migration |
| Priority levels | Add `priority SMALLINT DEFAULT 1` column + migration |
| Notification expiry | Add `expires_at DATETIME NULL` column + index |
| Read by multiple users | Requires a `notification_reads` junction table |
| Notification grouping | Add `group_id VARCHAR(36) NULL` column |
| Multi-database support | Change `DATABASE_URL` in `.env`; Alembic handles DDL differences |
