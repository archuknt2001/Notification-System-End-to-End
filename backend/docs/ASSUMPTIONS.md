# Assumptions and Design Decisions

This document records the assumptions made during implementation, the rationale behind each decision, and notes on how each could be changed.

---

## Authentication

**Assumption:** Requests are authenticated by trusting `X-Tenant-Id` and `X-User-Id` headers.

**Rationale:** The spec explicitly states "treat them as authenticated" and "do NOT build JWT." This is a deliberate challenge constraint to keep focus on the notification domain.

**Migration path:** The only file that needs to change is `app/middleware/context.py::get_tenant_context`. Replacing the header read with a JWT decode returns the same `TenantContext` object. All downstream layers (routes, services, repositories) are unchanged.

---

## User Visibility for Tenant-Level Callers

**Assumption:** A request with no `X-User-Id` header (user_id = None) is treated as a "tenant-level caller" that can only see tenant-wide notifications (user_id IS NULL rows).

**Rationale:** A caller with no user identity should not be able to see individual users' private notifications. This represents an admin or system-level caller. The alternative — letting them see everything — would create a security gap.

**Trade-off:** An admin user who genuinely needs to see all notifications must either provide a user ID or use a database query directly.

---

## UUID as String IDs

**Assumption:** The `id` column is `VARCHAR(36)` storing UUID v4 strings, not a native UUID or integer primary key.

**Rationale:** SQLite has no native UUID type. Using strings maximises portability across databases. UUIDs prevent ID enumeration attacks (guessing sequential integers). The `str(uuid.uuid4())` generation happens in Python, not as a database default, so it works identically across SQLite, PostgreSQL, and MySQL.

**Trade-off:** UUIDs are larger than integers (36 vs 4-8 bytes) and slightly slower to index. For a notification table this is negligible.

---

## SQLite for Development

**Assumption:** SQLite is used as the development database.

**Rationale:** Zero setup, file-based, works everywhere. The spec permits it. Alembic and SQLAlchemy abstract the database engine — switching to PostgreSQL or MySQL requires only a `DATABASE_URL` change in `.env`.

**Migration path:** Change `DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname` in `.env`. Run `alembic upgrade head`. No application code changes.

---

## Notification Type Validation

**Assumption:** The `type` field is validated at the Pydantic schema layer (as a `Literal` union), not as a database-level CHECK constraint.

**Rationale:** Adding a new notification type without a migration is a strong operational benefit. Database constraints would require a migration for each new type. The Pydantic `Literal` + `NOTIFICATION_TYPES` set in `notification_schema.py` is the single source of truth.

**Trade-off:** The database column accepts any string. If data is inserted outside the API (e.g. direct SQL), invalid types can exist. This is acceptable for a development-phase system.

---

## Polling vs WebSocket

**Assumption:** The frontend polls the API every 20 seconds rather than using WebSockets or Server-Sent Events.

**Rationale:** Polling is simpler, stateless, requires no infrastructure beyond the existing HTTP server, and is explicitly listed as a project requirement. It is appropriate for a notification system where sub-second latency is not required.

**Trade-off:** 20-second polling means up to 20 seconds of delay before a new notification appears. For most CRM use cases this is acceptable.

**Migration path:** Replace the `setInterval` in `NotificationContext.jsx` with a WebSocket connection or EventSource (SSE). The backend would need a WebSocket endpoint or SSE route, but the service and repository layers are unchanged.

---

## Optimistic UI Updates

**Assumption:** Mark-read and mark-all-read apply immediately in the UI before the API confirms success.

**Rationale:** This makes the UI feel instant. If the API call fails, the context refreshes to restore the correct state.

**Trade-off:** In the rare event of a network error after an optimistic update, the user may see a brief flicker as the state reverts.

---

## Client-Side Filtering

**Assumption:** Type and unread filters are applied client-side on the already-fetched page of notifications.

**Rationale:** The spec's filter requirements are for the current visible set. Client-side filtering gives instant response without additional API calls. The filter state lives in the context and is applied in `useNotifications`.

**Trade-off:** Filters only apply to the currently loaded page, not the full database. If the user has loaded page 1 of 5 and filters to "unread only," they see only the unread items from page 1. For a production feature with large datasets, server-side filtering (query parameters on `GET /notifications`) would be more complete. The API is already structured to support adding `type` and `read` query parameters without breaking changes.

---

## Pagination Strategy

**Assumption:** Offset-based pagination is used (`page` + `size` → `OFFSET` + `LIMIT`).

**Rationale:** Simple to implement and understand. Sufficient for moderate data volumes. The spec requires pagination without specifying a strategy.

**Trade-off:** Offset-based pagination can produce inconsistent results when new notifications are inserted between pages (a new unread notification on page 1 pushes items to page 2). Cursor-based pagination (keyset) would fix this but adds complexity.

---

## Seed Data Design

**Assumption:** Seed data uses fixed UUIDs for tenant and user IDs rather than randomly generated ones.

**Rationale:** Fixed IDs make the frontend tenant switcher, manual API testing, and demo scenarios fully reproducible across re-seeds. The `--force` flag clears and re-creates the exact same 20 rows.

---

## Single Notifications Table

**Assumption:** All notification types live in one table.

**Rationale:** The spec defines one notification model. A single table with a `type` discriminator column is simpler than a table-per-type inheritance and is sufficient for the current notification shape.

**Trade-off:** If notification types gain significantly different schemas (e.g. campaign notifications need campaign metadata), a `notification_metadata JSONB` column or a related table would be the natural extension.

---

## No Soft Delete

**Assumption:** Notifications are not soft-deleted. There is no delete API endpoint.

**Rationale:** The spec does not require deletion. Notifications are permanent records of business events. Adding soft delete is straightforward (add `deleted_at` column, add index, filter in `_visibility_filter`) but was out of scope.

---

## Mark-Read Visibility Check

**Assumption:** `mark_read` raises `ForbiddenError` (403) when a user tries to mark another user's private notification as read, even within the same tenant.

**Rationale:** This gives a meaningful distinction: 404 means "this doesn't exist for you" (cross-tenant), 403 means "this exists but you don't own it" (same tenant, wrong user). This prevents both information leakage and unauthorized state mutations.

**Alternative considered:** Always returning 404 for any failure (security through obscurity). Rejected because it makes debugging legitimate access issues unnecessarily difficult for developers.

---

## Error Detail Exposure

**Assumption:** When `DEBUG=false` (production default), 500 error responses return "An unexpected error occurred." instead of the actual exception message.

**Rationale:** Stack traces and internal error details should never be exposed to API consumers. The `DEBUG` flag in `.env` enables detailed errors for local development only.
