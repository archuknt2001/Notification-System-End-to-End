# Testing

## Overview

The test suite covers all layers of the backend: repository, service, API endpoints, and tenant isolation. Every test runs in a completely isolated in-memory SQLite database — no test can affect another.

**Result: 112 passed, 0 failed**

---

## Running Tests

```bash
cd backend
venv\Scripts\activate

# Run all tests
pytest

# Verbose output (shows each test name)
pytest -v

# Run a specific file
pytest tests/test_tenant_isolation.py -v

# Run a specific class
pytest tests/test_repository.py::TestMarkRead -v

# Run a specific test
pytest tests/test_api_notifications.py::TestCreateNotification::test_creates_tenant_wide -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run with short traceback (faster to read on failure)
pytest --tb=short
```

---

## Test Infrastructure

### conftest.py

All shared fixtures live in `tests/conftest.py`.

#### `db_session` fixture

Creates a fresh in-memory SQLite database for each test using `StaticPool`. StaticPool forces all SQLAlchemy connections to reuse a single underlying connection — this is critical for in-memory SQLite because each new connection would see an empty database.

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # single shared connection
)
Base.metadata.create_all(engine)
session = TestingSession()
yield session
# drop_all + dispose after test
```

#### `client` fixture

Wraps the FastAPI `TestClient` with two overrides:
1. Swaps `app.database.session.engine` to the test engine, so the lifespan's `Base.metadata.create_all` runs on the test database (idempotent since tables already exist).
2. Overrides `get_db` to always yield the test session.

```python
db_module.engine = db_session.bind
app.dependency_overrides[get_db] = override_get_db
```

Both overrides are restored after each test.

#### `seeded` fixture

Creates 10 notifications covering all visibility combinations:

| Key | Tenant | User | Read |
|---|---|---|---|
| `a_wide_unread_1` | A | NULL (tenant-wide) | No |
| `a_wide_unread_2` | A | NULL (tenant-wide) | No |
| `a_wide_read` | A | NULL (tenant-wide) | Yes |
| `a1_unread_1` | A | USER_A1 | No |
| `a1_unread_2` | A | USER_A1 | No |
| `a1_read` | A | USER_A1 | Yes |
| `a2_unread` | A | USER_A2 | No |
| `a2_read` | A | USER_A2 | Yes |
| `b_wide_unread` | B | NULL (tenant-wide) | No |
| `b1_unread` | B | USER_B1 | No |

**Expected unread counts from seeded data:**
- A1 visible: 4 (2 wide + 2 own)
- A2 visible: 3 (2 wide + 1 own)
- A tenant-wide: 2
- B1 visible: 2 (1 wide + 1 own)

---

## Test Files

### tests/test_repository.py — 28 tests

Tests all 6 `NotificationRepository` methods directly, without going through HTTP.

| Class | Tests |
|---|---|
| `TestCreate` | Creates with correct fields, tenant-wide default, persists to DB |
| `TestFindVisible` | User sees own + wide, not other user's private, not other tenant, ordering, pagination, total count, empty result |
| `TestFindById` | Finds existing, raises NotFoundError for wrong tenant, raises NotFoundError for missing ID |
| `TestCountUnread` | Counts visible unread only, zero after mark-all, tenant-level caller, isolation across tenants |
| `TestMarkRead` | Marks tenant-wide, marks own, idempotent, ForbiddenError wrong user, NotFoundError cross-tenant, NotFoundError missing, decrements count |
| `TestMarkAllRead` | Marks all visible, returns correct updated count, idempotent on second call, no effect on other tenant, correct handling of same-tenant different user |

### tests/test_service.py — 28 tests

Tests `NotificationService` and `EventService` directly against the repository.

| Class | Tests |
|---|---|
| `TestNotificationServiceCreate` | Returns NotificationRead, strips whitespace, ValidationError on invalid type, user_id set, tenant-wide default |
| `TestNotificationServiceList` | Returns NotificationList, pagination math, page 2 has_prev, disjoint pages, ordering, no cross-tenant items |
| `TestNotificationServiceUnreadCount` | Correct count, zero after mark-all |
| `TestNotificationServiceMarkRead` | Returns NotificationRead, NotFoundError cross-tenant, ForbiddenError wrong user |
| `TestNotificationServiceMarkAllRead` | Returns updated count, zero unread after, other tenant unaffected |
| `TestEventServiceMemberInvited` | Tenant-wide notification, visible to all users |
| `TestEventServiceCreatorReply` | User-specific, only recipient sees it, preview truncated |

### tests/test_api_notifications.py — 28 tests

End-to-end HTTP tests for all 5 notification endpoints.

| Class | Tests |
|---|---|
| `TestCreateNotification` | Tenant-wide, user-specific, invalid type 422, missing title 422, missing tenant 422, has id and created_at |
| `TestUnreadCount` | Returns count, decreases after mark-all, tenant A and B independent, missing tenant 422 |
| `TestListNotifications` | Data + meta structure, default page, custom page/size, disjoint pages, all items in tenant, no other users' items, unread first ordering, has_prev false on page 1, missing tenant 422 |
| `TestMarkRead` | Marks read, idempotent, cross-tenant 404, wrong user 403, missing ID 404, missing tenant 422 |
| `TestMarkAllRead` | Marks all, idempotent second call, no effect on other tenant, missing tenant 422 |

### tests/test_api_events.py — 16 tests

End-to-end HTTP tests for all 8 event endpoints.

| Class | Tests |
|---|---|
| `TestMemberInvited` | Tenant-wide type, visible to all tenant users, not visible to other tenant, missing tenant 422 |
| `TestCreatorReply` | User-specific, only recipient sees it |
| `TestCampaignEvents` | campaign_started and campaign_completed both tenant-wide |
| `TestPaymentReceived` | User-specific targeting |
| `TestReportReady` | User-specific targeting |
| `TestInvoiceDue` | Overdue text, future due text, "due tomorrow" text |
| `TestSystemAlert` | Tenant-wide when no user_id, user-specific when user_id given |

### tests/test_tenant_isolation.py — 12 tests

Dedicated security tests — the most critical test file.

| Class | Tests |
|---|---|
| `TestListIsolation` | Tenant A has no Tenant B rows, Tenant B has no Tenant A rows, IDs completely disjoint, A2 cannot see A1 private, A1 cannot see A2 private, both users see tenant-wide |
| `TestUnreadCountIsolation` | Counts independent per tenant, A1 and A2 have independent counts |
| `TestMarkReadIsolation` | Cannot mark other tenant's notification, cannot mark other user's private, mark-all scoped to tenant |
| `TestEventIsolation` | member_invited not visible to other tenant, creator_reply not visible to other tenant, notification created in correct tenant |
| `TestSameUserIdDifferentTenants` | Same user ID string in two tenants stays completely isolated |

---

## Coverage Map

| Spec Requirement | Test Class | File |
|---|---|---|
| Tenant isolation — list | `TestListIsolation` | test_tenant_isolation.py |
| Tenant isolation — count | `TestUnreadCountIsolation` | test_tenant_isolation.py |
| Tenant isolation — mark-read | `TestMarkReadIsolation` | test_tenant_isolation.py |
| Tenant isolation — events | `TestEventIsolation` | test_tenant_isolation.py |
| Same-user-ID edge case | `TestSameUserIdDifferentTenants` | test_tenant_isolation.py |
| Repository create | `TestCreate` | test_repository.py |
| Repository find_visible | `TestFindVisible` | test_repository.py |
| Repository find_by_id | `TestFindById` | test_repository.py |
| Repository count_unread | `TestCountUnread` | test_repository.py |
| Repository mark_read | `TestMarkRead` | test_repository.py |
| Repository mark_all_read | `TestMarkAllRead` | test_repository.py |
| Service create | `TestNotificationServiceCreate` | test_service.py |
| Service list (pagination) | `TestNotificationServiceList` | test_service.py |
| Service unread count | `TestNotificationServiceUnreadCount` | test_service.py |
| Service mark_read | `TestNotificationServiceMarkRead` | test_service.py |
| Service mark_all_read | `TestNotificationServiceMarkAllRead` | test_service.py |
| Event member_invited | `TestEventServiceMemberInvited` | test_service.py |
| Event creator_reply | `TestEventServiceCreatorReply` | test_service.py |
| API POST /notifications | `TestCreateNotification` | test_api_notifications.py |
| API GET /notifications | `TestListNotifications` | test_api_notifications.py |
| API GET /unread-count | `TestUnreadCount` | test_api_notifications.py |
| API PATCH /read-all | `TestMarkAllRead` | test_api_notifications.py |
| API PATCH /{id}/read | `TestMarkRead` | test_api_notifications.py |
| API events (all 8) | `TestMemberInvited`, etc. | test_api_events.py |
| Sorting (unread first) | `test_ordering_*`, `test_unread_first_*` | test_repository.py, test_api_notifications.py |
| Pagination | `test_pagination_*`, `test_pages_are_disjoint` | test_repository.py, test_service.py, test_api_notifications.py |
| Wrong tenant — 404 | `test_raises_not_found_cross_tenant`, `test_cross_tenant_returns_404` | all files |
| Wrong user — 403 | `test_raises_forbidden_for_other_users_notification` | test_repository.py, test_service.py |
| Input validation — 422 | `test_invalid_type_returns_422`, `test_missing_*` | test_api_notifications.py |

---

## Known Warnings

The test suite produces one warning:

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient`
is deprecated; install `httpx2` instead.
```

This is a cosmetic warning from Starlette about the TestClient transport layer. It does not affect test results and will resolve automatically when `httpx2` achieves broader ecosystem adoption.
