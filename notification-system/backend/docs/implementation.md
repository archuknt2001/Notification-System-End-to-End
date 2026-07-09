# Implementation Plan

---

## Phase 1 — Project Setup ✅ COMPLETE

**Goal:** Wire all foundational infrastructure so the app can start cleanly.

### What was built

| File | Purpose |
|------|---------|
| `app/utils/__init__.py` | Utils sub-package marker |
| `app/utils/pagination.py` | `PaginationParams` FastAPI dependency + `build_pagination_meta` helper |
| `app/main.py` | FastAPI app factory — CORS, lifespan startup, global exception handlers, `/health` endpoint |
| `app/core/config.py` | Updated: added `field_validator` for `allowed_origins` to accept comma-string or JSON array |
| `alembic.ini` | Alembic config — URL placeholder overridden in `env.py` |
| `alembic/env.py` | Migration environment — reads `settings.database_url`, imports `Base.metadata` |
| `alembic/script.py.mako` | Migration file template |
| `alembic/versions/` | Empty directory, ready for Phase 2 migration |
| `requirements.txt` | Updated to Python 3.14-compatible pins |
| `.env` | Fixed `ALLOWED_ORIGINS` to JSON array format for pydantic-settings 2.x |

### Verified
- `GET /health` → `{"status": "ok", "version": "1.0.0"}` ✅
- Unknown routes → 404 ✅
- App imports without errors ✅

### Architecture decisions
- `main.py` uses `create_app()` factory — makes the app testable by importing without side effects.
- Exception handlers translate domain exceptions (`NotFoundError`, `ForbiddenError`, `ValidationError`) to consistent JSON envelopes. Controllers never catch these manually.
- `Base.metadata.create_all()` runs on startup for dev convenience; Alembic handles production migrations.
- `PaginationParams` is a `@dataclass` + `Query` dependency — no duplication across endpoints.

---

## Phase 2 — Database, Models, Migration, Seed Data ✅ COMPLETE

**Goal:** Define the `Notification` ORM model, generate the first Alembic migration, and seed demo data for two tenants.

### What was built

| File | Purpose |
|------|---------|
| `app/models/notification.py` | SQLAlchemy ORM model — 9 columns, 4 explicit indexes |
| `app/models/__init__.py` | Re-exports `Notification`; Alembic imports this package |
| `alembic/env.py` | Updated to `import app.models` for autogenerate discovery |
| `alembic/versions/bb8819ae44fc_create_notifications_table.py` | First migration — creates table + all indexes |
| `seed.py` | Demo seed — 20 rows, 2 tenants × 10, all 11 notification types |

### Seed data summary
- **Tenant A** (`tenant-stellar-0001`): 10 rows — Alice (A1) and Bob (A2)
- **Tenant B** (`tenant-nova-00001`): 10 rows — Carol (B1) and Dave (B2)
- **Tenant-wide** (`user_id = NULL`): 8 rows
- **User-specific**: 12 rows
- **Unread**: 14 rows — sufficient to demonstrate badge and list
- **Read**: 6 rows — demonstrates read/unread styling

### Verified
- `alembic upgrade head` runs cleanly ✅
- All 9 columns and 5 indexes present in SQLite ✅
- `python seed.py` inserts 20 rows ✅
- Re-running without `--force` skips (idempotent) ✅
- `--force` clears and re-seeds ✅

---

## Phase 3 — Authentication Middleware ✅ COMPLETE

**Goal:** Extract tenant and user identity from request headers via FastAPI dependency injection. Zero coupling between HTTP transport and business logic.

### What was built

| File | Purpose |
|------|---------|
| `app/middleware/context.py` | `TenantContext` frozen dataclass + `get_tenant_context` dependency |
| `app/middleware/__init__.py` | Re-exports both symbols |
| `app/main.py` | Added `RequestValidationError` + `StarletteHTTPException` handlers |

### How it works
- Every route that needs tenant awareness declares `ctx: TenantContext = Depends(get_tenant_context)`.
- `X-Tenant-Id` is required → missing = 422 (our envelope), blank = 401.
- `X-User-Id` is optional → None means tenant-wide / system caller.
- Service and repository layers receive plain `str` values — no HTTP awareness.

### JWT migration path
Only `get_tenant_context` needs to change — decode Bearer token, extract claims, return the same `TenantContext`. All routes and all downstream layers stay unchanged.

### Verified (5 cases)
| Case | Input | Expected | Result |
|---|---|---|---|
| 1 | Both headers present | 200, ctx populated | ✅ |
| 2 | Tenant only, no user | 200, user_id=None | ✅ |
| 3 | Missing X-Tenant-Id | 422 our envelope + errors array | ✅ |
| 4 | Blank X-Tenant-Id | 401 our envelope | ✅ |
| 5 | Padded whitespace | 200, values stripped | ✅ |

---

## Phase 4 — Repository Layer ✅ COMPLETE

**Goal:** Implement the only database-access layer. Zero SQL in any other layer.

### What was built

| File | Purpose |
|------|---------|
| `app/repositories/notification_repository.py` | All 6 methods + `_visibility_filter` helper |
| `app/repositories/__init__.py` | Re-exports `NotificationRepository` |

### Methods

| Method | Description |
|---|---|
| `create()` | Insert new notification, return saved instance |
| `find_visible()` | Paginated list — unread first, newest first; returns `(items, total)` |
| `find_by_id()` | Fetch by ID within tenant — raises `NotFoundError` on miss or cross-tenant guess |
| `count_unread()` | Scalar count for the bell badge |
| `mark_read()` | Sets `read=True`, `read_at=now`; raises `ForbiddenError` for wrong-user access |
| `mark_all_read()` | Bulk UPDATE, returns count of rows changed |

### Key design choices
- `_visibility_filter` is the single canonical expression for the visibility rule — used by `find_visible`, `count_unread`, `mark_all_read` consistently.
- `mark_read` does a two-step check: tenant isolation first (`find_by_id`), then user visibility — giving a clear 404 vs 403 distinction.
- `mark_all_read` uses a single bulk `UPDATE` (not N individual updates).

### Verified (13 cases)
All 6 methods ✅ — create, find_visible (ordering, pagination, visibility), find_by_id (cross-tenant 404, missing id), count_unread (count matches manual), mark_read (idempotent, cross-tenant 404, wrong-user 403, tenant-wide OK), mark_all_read (zeroes unread, TENANT_B untouched)

---

## Phase 5 — Service Layer ✅ COMPLETE

**Goal:** Business logic layer between the API controllers (Phase 6) and the repository (Phase 4).

### What was built

| File | Purpose |
|------|---------|
| `app/schemas/notification_schema.py` | Pydantic models: `NotificationCreate`, `NotificationRead`, `NotificationList`, `UnreadCountRead` |
| `app/schemas/__init__.py` | Re-exports all schemas |
| `app/services/notification_service.py` | `NotificationService` — all 5 methods |
| `app/services/event_service.py` | `EventService` — 7 business events |
| `app/services/__init__.py` | Re-exports both services |

### NotificationService methods
| Method | Description |
|---|---|
| `create()` | Validates type, delegates to repo, returns `NotificationRead` |
| `list_notifications()` | Pagination math, returns typed `NotificationList` |
| `get_unread_count()` | Returns `UnreadCountRead` for badge |
| `mark_read()` | Delegates to repo with 404/403 semantics |
| `mark_all_read()` | Returns `{updated: int}` summary |

### EventService events
`member_invited` (tenant-wide), `creator_reply` (user-specific), `campaign_started`, `campaign_completed`, `payment_received`, `invoice_due` (smart urgency text), `report_ready`, `system_alert`

### Verified (16 cases)
create, create invalid type, list (ordering + visibility + pagination), get_unread_count, mark_read (NotFoundError + ForbiddenError), mark_all_read (zeroes unread + isolation), member_invited (tenant-wide, visible to all users, hidden from other tenant), creator_reply (user-specific, Alice sees it Bob does not), preview truncation — all ✅

---

## Phase 6 — REST APIs ✅ COMPLETE

**Goal:** Five production-ready REST endpoints wired through TenantContext -> NotificationService -> Repository.

### What was built

| File | Purpose |
|------|---------|
| `app/api/v1/__init__.py` | v1 package marker |
| `app/api/v1/notifications.py` | All 5 endpoints with dependency injection |
| `app/api/__init__.py` | Assembles versioned routers into `api_router` |
| `app/main.py` | Mounts `api_router` at `/api/v1` |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/notifications` | Create notification (tenant-wide or user-specific) |
| `GET` | `/api/v1/notifications` | List visible notifications — paginated, unread first |
| `GET` | `/api/v1/notifications/unread-count` | Unread count for bell badge |
| `PATCH` | `/api/v1/notifications/read-all` | Mark all visible unread as read |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark one notification as read |

### Verified (16 cases)
Missing tenant (422 envelope), POST tenant-wide, POST user-specific, POST invalid type (422), GET unread-count (Alice + Tenant B independent), GET list (ordering + visibility + tenant isolation), PATCH mark-read (200 + idempotent + 404 cross-tenant + 403 wrong-user + 404 missing), PATCH read-all (zeroes Alice unread, Tenant B unchanged), pagination meta — all ✅

---

## Phase 7 — Event System ✅ COMPLETE

**Goal:** Expose business event endpoints that go Controller -> EventService -> NotificationService -> Repository. Controllers never create notifications directly.

### What was built

| File | Purpose |
|------|---------|
| `app/api/v1/events.py` | 8 event endpoints, each with its own Pydantic request schema |
| `app/api/__init__.py` | Updated to include `events_router` |

### Endpoints

| Method | Path | Creates |
|--------|------|---------|
| `POST` | `/api/v1/events/member-invited` | Tenant-wide `member_invited` notification |
| `POST` | `/api/v1/events/creator-reply` | User-specific `new_reply` notification |
| `POST` | `/api/v1/events/campaign-started` | Tenant-wide `campaign_started` |
| `POST` | `/api/v1/events/campaign-completed` | Tenant-wide `campaign_completed` |
| `POST` | `/api/v1/events/payment-received` | User-specific `payment_received` |
| `POST` | `/api/v1/events/report-ready` | User-specific `report_ready` |
| `POST` | `/api/v1/events/invoice-due` | User-specific `invoice_due` (smart urgency text) |
| `POST` | `/api/v1/events/system-alert` | Tenant-wide or user-specific `system_alert` |

### Verified (13 cases)
All 8 endpoints fire correctly, types/targeting verified, tenant isolation confirmed, missing-tenant 422, unread count increments after events — all ✅

---

## Phase 8 & 9 — Frontend ✅ COMPLETE

**Goal:** Production-quality React UI with notification bell, drawer, polling, relative time, and filters.

### What was built

| File | Purpose |
|------|---------|
| `frontend/package.json` | React 19, Vite 6, TailwindCSS 3, Axios 1.7, date-fns 4 |
| `frontend/vite.config.js` | Dev server on :5173, proxy `/api` to backend :8000 |
| `frontend/tailwind.config.js` | Custom fade-in/slide-in animations, dark mode class |
| `src/services/api.js` | All HTTP calls — notifications + 7 event endpoints |
| `src/context/NotificationContext.jsx` | Global state: list, unread count, identity, polling, optimistic updates |
| `src/hooks/useNotifications.js` | Convenience hook with client-side `filteredNotifications` |
| `src/utils/relativeTime.js` | ISO string to "X minutes ago" via date-fns |
| `src/utils/notificationIcons.js` | Type → emoji + Tailwind colour classes |
| `src/components/NotificationBell.jsx` | Bell icon + animated red badge (99+ cap) |
| `src/components/NotificationDrawer.jsx` | Slide-in panel: list, skeleton, empty state, mark-all, refresh, load-more |
| `src/components/NotificationCard.jsx` | Read/unread styling, relative time, personal/team badge, type badge |
| `src/components/SkeletonCard.jsx` | Animated loading placeholder |
| `src/components/FilterBar.jsx` | Type dropdown + unread-only toggle button |
| `src/components/DemoTrigger.jsx` | 7-button event panel with spinner + toast feedback |
| `src/App.jsx` | TenantSwitcher header, identity card, layout, provider root |

### Phase 9 features included
- Polling every 20 seconds (configurable via `POLL_INTERVAL`)
- Relative timestamps via date-fns `formatDistanceToNowStrict`
- Type filter dropdown (all 11 types)
- Unread-only toggle
- Optimistic mark-read and mark-all-read

### Build verified
```
dist/assets/index.css   19.56 kB (gzip 4.31 kB)
dist/assets/index.js   255.08 kB (gzip 83.31 kB)
Built in 3.30s — exit 0
```

---

## Phase 10 — Testing ✅ COMPLETE

**Goal:** Pytest suite covering all spec requirements — tenant isolation, pagination, sorting, mark-read, wrong-tenant access, repository, service, and API endpoints.

### What was built

| File | Purpose |
|------|---------|
| `pytest.ini` | Test configuration — testpaths, asyncio_mode |
| `tests/__init__.py` | Package marker |
| `tests/conftest.py` | Fixtures: StaticPool in-memory SQLite, db_session, client (engine swap), seeded data, make_notification helper |
| `tests/test_repository.py` | 28 tests — all 6 repository methods + isolation |
| `tests/test_service.py` | 28 tests — NotificationService (5 methods) + EventService (3 scenarios) |
| `tests/test_api_notifications.py` | 28 tests — all 5 notification endpoints, happy path + all error cases |
| `tests/test_api_events.py` | 16 tests — all 8 event endpoints |
| `tests/test_tenant_isolation.py` | 12 tests — dedicated cross-tenant security: list, count, mark-read, events, same-user-ID edge case |

### Test infrastructure key decisions
- `StaticPool` — all SQLAlchemy connections share one in-memory SQLite connection, preventing "no such table" across connections
- Engine swap in `client` fixture — patches `app.database.session.engine` before `TestClient.__enter__` fires the lifespan's `create_all`
- `dependency_overrides[get_db]` — all HTTP requests use the test session
- Each test gets a fresh database — no inter-test contamination

### Final result
```
112 passed, 0 failed, 1 warning (Starlette httpx deprecation — cosmetic only)
```

### Coverage by spec requirement
| Requirement | Tests |
|---|---|
| Tenant isolation — list | `TestListIsolation` (6 tests) |
| Tenant isolation — count | `TestUnreadCountIsolation` (2 tests) |
| Tenant isolation — mark-read | `TestMarkReadIsolation` (3 tests) |
| Tenant isolation — events | `TestEventIsolation` (3 tests) |
| Same user-ID across tenants | `TestSameUserIdDifferentTenants` (1 test) |
| Unread count | `TestCountUnread`, `TestUnreadCount` |
| Pagination | `test_pagination_*`, `test_pages_are_disjoint`, `test_has_prev_*` |
| Sorting (unread first, newest first) | `test_ordering_*`, `test_unread_first_*` |
| Mark read | `TestMarkRead`, `TestMarkRead` |
| Mark all read | `TestMarkAllRead`, `TestMarkAllRead` |
| Wrong tenant access | `test_cross_tenant_*`, `test_raises_not_found_cross_tenant` |
| Repository layer | `TestCreate`, `TestFindVisible`, `TestFindById`, `TestCountUnread`, `TestMarkRead`, `TestMarkAllRead` |
| Service layer | `TestNotificationService*`, `TestEventService*` |
| API endpoints | `TestCreateNotification`, `TestUnreadCount`, `TestListNotifications`, `TestMarkRead`, `TestMarkAllRead` |

---

## Phase 11 — Documentation ✅ COMPLETE

**Goal:** Comprehensive documentation covering every aspect of the system for developers, reviewers, and future contributors.

### What was built

| File | Description |
|---|---|
| `README.md` (project root) | Full setup guide, project structure, API table, frontend features, test instructions, env vars |
| `docs/ARCHITECTURE.md` | System layers, request lifecycle, event pipeline, tenant isolation design, DI map, exception handling, response envelope, frontend architecture, DB architecture, security boundaries |
| `docs/API_SPEC.md` | All 13 endpoints with request/response examples, field tables, error codes, visibility rules |
| `docs/DATABASE_SCHEMA.md` | Full column reference, all 4 indexes with rationale, business rules, migration history, seed data breakdown, future schema considerations |
| `docs/TESTING.md` | Test infrastructure (StaticPool, engine swap, fixtures), per-file breakdown of all 112 tests, full coverage map against spec requirements |
| `docs/ASSUMPTIONS.md` | 14 documented design decisions with rationale, trade-offs, and migration paths |
| `docs/FUTURE_ENHANCEMENTS.md` | 11-phase roadmap: WebSocket, JWT, event bus, email/push, preferences, cursor pagination, server-side filters, archive/delete, scheduled notifications, analytics, Redis scale |

### Documentation principles applied
- Every assumption documented with "why" and "how to change"
- Every future enhancement shows exactly which files change and which stay the same
- API spec includes examples for all success and error cases
- Test coverage map cross-references every spec requirement to a specific test class
