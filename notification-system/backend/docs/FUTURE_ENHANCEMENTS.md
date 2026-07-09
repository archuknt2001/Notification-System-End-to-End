# Future Enhancements

This document describes the planned evolution path for the notification system as it integrates deeper into the CRM platform.

---

## Phase A — Real-Time Delivery (WebSocket / SSE)

**Current:** Frontend polls `/notifications/unread-count` every 20 seconds.

**Enhancement:** Replace polling with a persistent connection so notifications appear instantly.

**Option 1 — Server-Sent Events (SSE)**
- Simpler than WebSocket; HTTP-based; one-way (server to client)
- Add `GET /notifications/stream` endpoint using FastAPI's `EventSourceResponse`
- Frontend replaces `setInterval` with `new EventSource('/api/v1/notifications/stream')`
- No changes to service or repository layers

**Option 2 — WebSocket**
- Bidirectional; supports future use cases (typing indicators, live updates)
- Add `WS /ws/notifications` endpoint
- Requires a connection registry (in-memory for single-server; Redis pub/sub for multi-server)

**What does NOT change:** `NotificationService`, `NotificationRepository`, `Notification` model.

---

## Phase B — JWT Authentication

**Current:** Tenant and user identity from `X-Tenant-Id` / `X-User-Id` headers.

**Enhancement:** Replace headers with a signed JWT Bearer token.

**Steps:**
1. Change `app/middleware/context.py::get_tenant_context` to:
   - Extract Bearer token from `Authorization` header
   - Verify signature with a public key
   - Extract `tenant_id` and `user_id` from token claims
   - Return `TenantContext(tenant_id, user_id)` — same as today

2. Add `app/core/jwt.py` with decode helpers.

**What does NOT change:** Every route, service, repository, schema, and model file is unchanged. This is by design.

---

## Phase C — Event Bus Integration

**Current:** Events are triggered via HTTP endpoints (`POST /events/member-invited`).

**Enhancement:** Replace HTTP event triggers with a message queue consumer.

**Architecture:**
```
CRM Service → Kafka / RabbitMQ Topic → Notification Consumer → EventService → NotificationService → DB
```

**Steps:**
1. Create `app/consumers/notification_consumer.py` — subscribes to the event bus topic
2. Map event message types to `EventService` method calls
3. `EventService` is unchanged — it doesn't know where events come from

**Supported brokers:** Kafka (via `aiokafka`), RabbitMQ (via `aio-pika`), AWS SQS (via `aiobotocore`)

---

## Phase D — Email and Push Notifications

**Enhancement:** When a notification is created, also dispatch an email and/or push notification.

**Architecture:**
```
NotificationService.create()
    → (existing) Repository.create()        — persist to DB
    → (new) EmailDispatcher.send()          — send email
    → (new) PushDispatcher.send()           — send push notification
```

**Implementation approach:**
- Add `app/dispatchers/email_dispatcher.py` and `push_dispatcher.py`
- Call dispatchers from `NotificationService.create()` after successful persistence
- Use async fire-and-forget (or a background task queue) so dispatch failures don't affect the API response

**Email providers:** SendGrid, AWS SES, Postmark
**Push providers:** Firebase Cloud Messaging, Apple APNs, OneSignal

---

## Phase E — Notification Preferences

**Enhancement:** Users can opt out of specific notification types or delivery channels.

**New table:**
```sql
CREATE TABLE notification_preferences (
    id          VARCHAR(36) PRIMARY KEY,
    tenant_id   VARCHAR(36) NOT NULL,
    user_id     VARCHAR(36) NOT NULL,
    type        VARCHAR(50),           -- NULL = all types
    channel     VARCHAR(20) NOT NULL,  -- 'in_app', 'email', 'push'
    enabled     BOOLEAN NOT NULL DEFAULT true,
    updated_at  DATETIME NOT NULL
);
```

**New API endpoints:**
- `GET /notifications/preferences` — get user preferences
- `PUT /notifications/preferences` — update preferences

**Integration:** `NotificationService.create()` checks preferences before dispatching to each channel.

---

## Phase F — Pagination Improvements

**Current:** Offset-based pagination (`page` + `size`).

**Enhancement:** Cursor-based pagination (keyset) for consistent results when new notifications arrive.

**Implementation:**
- Add `cursor` parameter to `GET /notifications` — a base64-encoded `(created_at, id)` pair
- Replace `OFFSET` with `WHERE (created_at, id) < (?, ?)` in the repository query
- Return `next_cursor` in the response meta instead of `total_pages`

**Benefit:** No duplicate or missing items when new notifications are inserted between pages.

---

## Phase G — Server-Side Filtering

**Current:** Type and unread filters are applied client-side on the loaded page.

**Enhancement:** Pass filter parameters directly to the API query.

**API change:**
```
GET /notifications?type=new_reply&read=false&page=1&size=20
```

**Repository change:**
```python
def find_visible(self, tenant_id, user_id, offset, limit,
                 type_filter=None, unread_only=False):
    query = base_query
    if type_filter:
        query = query.filter(Notification.type == type_filter)
    if unread_only:
        query = query.filter(Notification.read.is_(False))
    ...
```

**Frontend change:** Pass filter state to the API call instead of filtering the response.

---

## Phase H — Notification Archiving and Deletion

**Enhancement:** Allow users to archive or delete notifications.

**New columns:**
- `archived_at DATETIME NULL` — soft archive
- `deleted_at DATETIME NULL` — soft delete

**New API endpoints:**
- `PATCH /notifications/{id}/archive`
- `DELETE /notifications/{id}` (sets `deleted_at`, not physical delete)
- `GET /notifications/archived` — list archived notifications

**Repository change:** Add `archived_at IS NULL AND deleted_at IS NULL` to all visibility filters.

---

## Phase I — Scheduled Notifications

**Enhancement:** Allow notifications to be scheduled for future delivery.

**New column:**
```sql
ALTER TABLE notifications ADD COLUMN scheduled_at DATETIME NULL;
```

**Behaviour:** Notifications with `scheduled_at > NOW()` are not returned by `find_visible` until their scheduled time.

**Background task:** A scheduler (APScheduler or Celery Beat) marks scheduled notifications as "due" at the correct time and delivers them.

---

## Phase J — Analytics and Audit

**Enhancement:** Track notification engagement metrics.

**New table:**
```sql
CREATE TABLE notification_events (
    id              VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL,
    tenant_id       VARCHAR(36) NOT NULL,
    user_id         VARCHAR(36),
    event_type      VARCHAR(20) NOT NULL,  -- 'created', 'read', 'dismissed'
    occurred_at     DATETIME NOT NULL
);
```

**Metrics to track:**
- Open rate per notification type
- Average time-to-read
- Notification volume per tenant per day
- Most active notification types

---

## Phase K — Performance at Scale

At high notification volume, the following optimisations apply:

| Concern | Solution |
|---|---|
| High read volume on `/unread-count` | Redis cache per (tenant_id, user_id), invalidated on create/mark_read |
| High write volume | Background task queue (Celery + Redis) for notification creation |
| Database growth | Partition `notifications` table by `tenant_id` (PostgreSQL) |
| Large tenant lists | Cursor-based pagination (Phase F) |
| Cross-region tenants | Per-tenant database sharding or read replicas |

---

## Summary Roadmap

| Phase | Feature | Complexity | Impact |
|---|---|---|---|
| A | WebSocket / SSE | Medium | High — real-time UX |
| B | JWT authentication | Low | Critical — production auth |
| C | Event bus consumer | Medium | High — decoupled architecture |
| D | Email + push dispatch | Medium | High — multi-channel |
| E | Notification preferences | Medium | Medium — user control |
| F | Cursor pagination | Low | Medium — consistency |
| G | Server-side filters | Low | Medium — performance |
| H | Archive and delete | Low | Medium — lifecycle |
| I | Scheduled notifications | Medium | Medium — automation |
| J | Analytics and audit | Medium | Medium — insights |
| K | Redis cache + scale | High | Critical at scale |
