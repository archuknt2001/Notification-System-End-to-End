# Architecture

## System Overview

The notification system is built on Clean Architecture principles. Every layer has a single responsibility and depends only on the layer below it. The HTTP transport layer has zero knowledge of business logic; the business logic layer has zero knowledge of HTTP.

```
┌─────────────────────────────────────────────────────┐
│                     FRONTEND                        │
│  React + Vite + TailwindCSS                         │
│  NotificationBell · Drawer · Cards · Filters        │
│  Polling every 20s via NotificationContext          │
└────────────────────┬────────────────────────────────┘
                     │  HTTP (Axios, /api/v1/*)
                     │
┌────────────────────▼────────────────────────────────┐
│                  REST API LAYER                      │
│  FastAPI  ·  app/api/v1/notifications.py            │
│           ·  app/api/v1/events.py                   │
│  Responsibilities:                                  │
│  · Parse request headers → TenantContext            │
│  · Validate request body (Pydantic schemas)         │
│  · Call service layer                               │
│  · Serialize response envelope                      │
│  No business logic. No DB access.                   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               MIDDLEWARE / CONTEXT                  │
│  app/middleware/context.py                          │
│  · Extracts X-Tenant-Id + X-User-Id from headers   │
│  · Returns immutable TenantContext dataclass        │
│  · JWT-ready: only this file changes on migration  │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               SERVICE LAYER                         │
│                                                     │
│  NotificationService              EventService      │
│  · create()                       · member_invited()│
│  · list_notifications()           · creator_reply() │
│  · get_unread_count()             · campaign_*()    │
│  · mark_read()                    · payment_*()     │
│  · mark_all_read()                · report_ready()  │
│                                   · system_alert()  │
│                                                     │
│  Responsibilities:                                  │
│  · All business rules and validation                │
│  · Pagination math                                  │
│  · Schema ↔ ORM mapping                            │
│  No FastAPI imports. No DB imports.                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              REPOSITORY LAYER                       │
│  NotificationRepository                             │
│  · create()         · find_visible()                │
│  · find_by_id()     · count_unread()                │
│  · mark_read()      · mark_all_read()               │
│                                                     │
│  Responsibilities:                                  │
│  · ALL database access — nothing else touches DB    │
│  · Tenant isolation enforced via _visibility_filter │
│  · Raises domain exceptions (NotFoundError, etc.)   │
│  No FastAPI. No business logic.                     │
└────────────────────┬────────────────────────────────┘
                     │  SQLAlchemy ORM
┌────────────────────▼────────────────────────────────┐
│                  DATABASE                           │
│  SQLite (dev) · PostgreSQL/MySQL (prod)             │
│  Single table: notifications                        │
│  4 composite indexes for query performance          │
│  Alembic for schema migrations                      │
└─────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

A typical `GET /api/v1/notifications` request flows as follows:

```
1. Request arrives with headers: X-Tenant-Id, X-User-Id
   │
2. get_tenant_context() dependency resolves
   → Validates X-Tenant-Id is present and non-blank
   → Returns TenantContext(tenant_id="...", user_id="...")
   │
3. PaginationParams dependency resolves
   → Reads page / size from query string
   → Applies min/max bounds
   │
4. get_notification_service() dependency resolves
   → Instantiates NotificationService(db)
   │
5. Route handler calls:
   svc.list_notifications(tenant_id, user_id, page, size)
   │
6. NotificationService calls:
   repo.find_visible(tenant_id, user_id, offset, limit)
   │
7. NotificationRepository builds SQL:
   WHERE tenant_id = ? AND (user_id IS NULL OR user_id = ?)
   ORDER BY read ASC, created_at DESC
   LIMIT ? OFFSET ?
   │
8. ORM returns list[Notification]
   │
9. Service builds NotificationList schema (pagination math)
   │
10. Route serialises with model_dump(mode="json")
    → success_response(data=items, meta=pagination)
    │
11. JSON response returned to client
```

---

## Event Pipeline

The event system enforces that business logic never creates notifications directly:

```
Business Action (e.g. "user invited a member")
          │
          ▼
  Route Handler (POST /api/v1/events/member-invited)
  · Parses request body → MemberInvitedEvent schema
  · Calls EventService.member_invited(...)
          │
          ▼
  EventService.member_invited()
  · Constructs NotificationCreate payload
  · Sets targeting: user_id=None (tenant-wide)
  · Calls NotificationService.create(tenant_id, payload)
          │
          ▼
  NotificationService.create()
  · Validates notification type
  · Calls NotificationRepository.create(...)
          │
          ▼
  NotificationRepository.create()
  · Builds Notification ORM instance
  · db.add() → db.commit() → db.refresh()
  · Returns persisted Notification
          │
          ▼
  Response: 201 Created with notification JSON
```

---

## Tenant Isolation Architecture

Tenant isolation is enforced **structurally** at the repository layer, not through application-level checks in controllers or services.

```python
# _visibility_filter — the single source of truth for visibility
def _visibility_filter(self, tenant_id: str, user_id: str | None):
    tenant_filter = Notification.tenant_id == tenant_id
    if user_id is not None:
        user_filter = or_(
            Notification.user_id.is_(None),   # tenant-wide
            Notification.user_id == user_id,  # own notifications
        )
    else:
        user_filter = Notification.user_id.is_(None)  # tenant-level callers
    return and_(tenant_filter, user_filter)
```

This filter is used by **every** read operation: `find_visible`, `count_unread`, `mark_all_read`. It is impossible to bypass from any higher layer.

`mark_read` additionally verifies per-notification visibility before allowing the write, giving clear 404 (wrong tenant) vs 403 (wrong user) semantics.

---

## Dependency Injection Map

```
FastAPI Request
    │
    ├── get_tenant_context()       →  TenantContext
    │     (reads X-Tenant-Id, X-User-Id)
    │
    ├── get_db()                   →  Session
    │     (creates SQLAlchemy session, yields, closes)
    │
    ├── get_notification_service() →  NotificationService(db)
    │     (instantiated per request)
    │
    └── get_event_service()        →  EventService(db)
          (instantiated per request)
```

All dependencies are declared at the route level — services and repositories never receive request objects.

---

## Exception Handling Architecture

Domain exceptions flow upward and are caught by global handlers in `main.py`:

```
Repository raises NotFoundError / ForbiddenError / ValidationError
          │
          ▼
Service propagates (no catching)
          │
          ▼
Route propagates (no catching)
          │
          ▼
main.py exception handlers:
  NotFoundError       → 404  {"success": false, "message": "..."}
  ForbiddenError      → 403  {"success": false, "message": "..."}
  ValidationError     → 400  {"success": false, "message": "..."}
  RequestValidation   → 422  {"success": false, "errors": [...]}
  HTTPException       → passthrough with envelope
  Exception           → 500  (detail hidden in production)
```

Controllers never write `try/except` blocks. Error handling is fully centralised.

---

## Response Envelope

Every API response uses the same structure:

```json
{
  "success": true,
  "message": "Optional human-readable message",
  "data": { ... } | [ ... ],
  "meta": {
    "total": 42,
    "page": 1,
    "size": 20,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  },
  "errors": null
}
```

`meta` is included only on paginated list responses.
`errors` is included only on validation failures (422).

---

## Frontend Architecture

```
App.jsx
  └── NotificationProvider          (context, state, polling)
        ├── useNotifications()      (filtered list derivation)
        │
        ├── NotificationBell        (badge counter, toggle drawer)
        │     └── NotificationDrawer
        │           ├── FilterBar   (type dropdown, unread toggle)
        │           ├── SkeletonCard × 4  (loading state)
        │           ├── NotificationCard × N
        │           └── Load More button
        │
        └── DemoTrigger             (7 event buttons + toast)
```

**State flow:**
- `NotificationContext` owns: `notifications[]`, `unreadCount`, `meta`, `loading`, `identity`, `filter`
- `useNotifications` derives: `filteredNotifications` (client-side filter applied to the list)
- Components are fully controlled — they call context methods, never `api.js` directly

**Polling:**
- `setInterval` every 20s calls `fetchUnreadCount`
- If count changes, the full list is also refreshed
- Optimistic updates apply immediately; a failed request triggers a full re-fetch to restore consistency

---

## Database Architecture

```
notifications
┌─────────────┬──────────────┬────────────────────────────────────────┐
│ Column      │ Type         │ Notes                                  │
├─────────────┼──────────────┼────────────────────────────────────────┤
│ id          │ VARCHAR(36)  │ UUID primary key                       │
│ tenant_id   │ VARCHAR(36)  │ Required — every row belongs to tenant │
│ user_id     │ VARCHAR(36)  │ Nullable — NULL = tenant-wide          │
│ type        │ VARCHAR(50)  │ Validated at schema layer              │
│ title       │ VARCHAR(255) │                                        │
│ body        │ TEXT         │                                        │
│ read        │ BOOLEAN      │ Default False, server_default '0'      │
│ created_at  │ DATETIME(tz) │ UTC, set on create                     │
│ read_at     │ DATETIME(tz) │ Nullable, set when marked read         │
└─────────────┴──────────────┴────────────────────────────────────────┘

Indexes:
  ix_notifications_tenant_id          (tenant_id)
  ix_notifications_tenant_user        (tenant_id, user_id)
  ix_notifications_tenant_read        (tenant_id, read)
  ix_notifications_tenant_read_created (tenant_id, read, created_at)
```

The composite index `(tenant_id, read, created_at)` fully covers the primary list query: filter by tenant, sort unread first, sort newest first.

---

## Security Boundaries

| Boundary | Enforcement |
|---|---|
| Cross-tenant data access | `_visibility_filter` always ANDs `tenant_id = ?` |
| Cross-tenant ID guessing | `find_by_id` filters by both `id` AND `tenant_id` |
| Wrong-user mark-read | `mark_read` checks `user_id` before writing |
| Header injection | `get_tenant_context` strips whitespace, rejects blank |
| Input validation | Pydantic schemas with strict types and min/max lengths |
| Internal error exposure | 500 errors return generic message when `DEBUG=false` |
