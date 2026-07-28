# API Specification

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs`

---

## Authentication

All endpoints require the `X-Tenant-Id` header. `X-User-Id` is optional.

| Header | Required | Description |
|---|---|---|
| `X-Tenant-Id` | Yes | Tenant identifier. Missing or blank returns 401/422. |
| `X-User-Id` | No | User identifier. Omit for tenant-wide operations. |

---

## Standard Response Envelope

All responses share this structure:

```json
{
  "success": true,
  "message": "Optional message",
  "data": {},
  "meta": null,
  "errors": null
}
```

Error responses:

```json
{
  "success": false,
  "message": "Human-readable error",
  "data": null,
  "errors": [
    { "field": "header -> X-Tenant-Id", "message": "field required", "type": "missing" }
  ]
}
```

---

## Notification Object

All notification endpoints return this object (or arrays of it):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant-stellar-0001",
  "user_id": "user-alice-00000001",
  "type": "new_reply",
  "title": "@nova replied to your message",
  "body": "@nova replied: \"Sounds great, let's connect!\"",
  "read": false,
  "created_at": "2026-07-09T11:30:00+00:00",
  "read_at": null
}
```

`user_id` is `null` for tenant-wide notifications.
`read_at` is `null` when `read` is `false`.

---

## Notification Types

Allowed values for the `type` field:

| Type | Description |
|---|---|
| `member_invited` | A new team member was invited |
| `new_reply` | A creator replied to a message |
| `report_ready` | A report has been generated |
| `campaign_started` | A campaign went live |
| `campaign_completed` | A campaign finished |
| `payment_received` | A payment was received |
| `invoice_due` | An invoice is due or overdue |
| `warning` | A warning condition |
| `success` | A success event |
| `system_alert` | A system-level alert |
| `error` | An error event |

---

## Notification Endpoints

---

### POST /notifications

Create a notification.

**Headers:** `X-Tenant-Id` (required), `X-User-Id` (optional)

**Request body:**

```json
{
  "type": "system_alert",
  "title": "Scheduled maintenance",
  "body": "Platform offline Sunday 02:00–04:00 UTC.",
  "user_id": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Must be one of the allowed notification types |
| `title` | string | Yes | Max 255 characters. Leading/trailing whitespace stripped. |
| `body` | string | Yes | Notification body text. |
| `user_id` | string or null | No | Target user ID. `null` creates a tenant-wide notification. |

**Response: 201 Created**

```json
{
  "success": true,
  "message": "Notification created.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "tenant-stellar-0001",
    "user_id": null,
    "type": "system_alert",
    "title": "Scheduled maintenance",
    "body": "Platform offline Sunday 02:00–04:00 UTC.",
    "read": false,
    "created_at": "2026-07-09T11:30:00+00:00",
    "read_at": null
  }
}
```

**Errors:**
- `422` — Invalid type, missing title/body, missing X-Tenant-Id

---

### GET /notifications

List notifications visible to the current user. Unread first, newest first within each group.

**Headers:** `X-Tenant-Id` (required), `X-User-Id` (optional)

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number (1-based) |
| `size` | integer | 20 | Items per page (max 100) |

**Response: 200 OK**

```json
{
  "success": true,
  "data": [
    {
      "id": "...",
      "tenant_id": "tenant-stellar-0001",
      "user_id": "user-alice-00000001",
      "type": "new_reply",
      "title": "@nova replied to your message",
      "body": "@nova replied: \"Let's connect!\"",
      "read": false,
      "created_at": "2026-07-09T11:30:00+00:00",
      "read_at": null
    }
  ],
  "meta": {
    "total": 12,
    "page": 1,
    "size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Visibility rules:**
- Notifications where `user_id` matches the caller's `X-User-Id` are visible.
- Notifications where `user_id` is `null` (tenant-wide) are visible to all users in the tenant.
- Notifications from other tenants are never returned.

**Errors:**
- `422` — Missing X-Tenant-Id

---

### GET /notifications/unread-count

Get the count of unread notifications visible to the current user.

**Headers:** `X-Tenant-Id` (required), `X-User-Id` (optional)

**Response: 200 OK**

```json
{
  "success": true,
  "data": {
    "unread_count": 7
  }
}
```

**Errors:**
- `422` — Missing X-Tenant-Id

---

### PATCH /notifications/read-all

Mark all visible unread notifications as read in a single operation.

**Headers:** `X-Tenant-Id` (required), `X-User-Id` (optional)

**Request body:** none

**Response: 200 OK**

```json
{
  "success": true,
  "message": "7 notification(s) marked as read.",
  "data": {
    "updated": 7
  }
}
```

If there are no unread notifications, `updated` will be `0`. This is not an error.

**Errors:**
- `422` — Missing X-Tenant-Id

---

### PATCH /notifications/{id}/read

Mark a single notification as read.

**Headers:** `X-Tenant-Id` (required), `X-User-Id` (optional)

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | string (UUID) | The notification ID |

**Request body:** none

**Response: 200 OK**

```json
{
  "success": true,
  "message": "Notification marked as read.",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "tenant-stellar-0001",
    "user_id": null,
    "type": "system_alert",
    "title": "Scheduled maintenance",
    "body": "Platform offline Sunday 02:00–04:00 UTC.",
    "read": true,
    "created_at": "2026-07-09T11:30:00+00:00",
    "read_at": "2026-07-09T12:00:00+00:00"
  }
}
```

This operation is idempotent. Marking an already-read notification returns 200 with no change.

**Errors:**
- `404` — Notification does not exist within this tenant (also returned on cross-tenant ID guessing)
- `403` — Notification exists but is targeted at a different user
- `422` — Missing X-Tenant-Id

---

## Event Endpoints

Event endpoints simulate business events firing notifications. They demonstrate the Controller → EventService → NotificationService → Repository pipeline.

---

### POST /events/member-invited

Fire a member invitation event. Creates a **tenant-wide** notification.

**Request body:**

```json
{
  "invited_by": "Alice",
  "invitee_name": "Jordan Lee",
  "invitee_email": "jordan@example.com"
}
```

**Response: 201 Created** — Notification object (same structure as above)

---

### POST /events/creator-reply

Fire a creator reply event. Creates a **user-specific** notification.

**Request body:**

```json
{
  "recipient_user_id": "user-alice-00000001",
  "creator_handle": "@nova_style",
  "preview": "Sounds great, let's schedule a call!"
}
```

Preview text longer than 120 characters is automatically truncated with `...`.

---

### POST /events/campaign-started

Fire a campaign-started event. Creates a **tenant-wide** notification.

**Request body:**

```json
{
  "campaign_name": "Autumn Vibes 2025"
}
```

---

### POST /events/campaign-completed

Fire a campaign-completed event. Creates a **tenant-wide** notification.

**Request body:**

```json
{
  "campaign_name": "Summer Glow"
}
```

---

### POST /events/payment-received

Fire a payment-received event. Creates a **user-specific** notification.

**Request body:**

```json
{
  "recipient_user_id": "user-bob-000000001",
  "amount": "$8,500",
  "source": "BrandX Corp"
}
```

---

### POST /events/report-ready

Fire a report-ready event. Creates a **user-specific** notification.

**Request body:**

```json
{
  "recipient_user_id": "user-alice-00000001",
  "report_name": "Q3 Campaign Performance"
}
```

---

### POST /events/invoice-due

Fire an invoice-due event. Creates a **user-specific** notification. The urgency text in the title is determined automatically based on `due_in_days`.

**Request body:**

```json
{
  "recipient_user_id": "user-bob-000000001",
  "invoice_number": "INV-2024-099",
  "amount": "$2,500",
  "due_in_days": 3
}
```

| `due_in_days` | Title contains |
|---|---|
| `<= 0` | "is now overdue" |
| `1` | "is due tomorrow" |
| `> 1` | "is due in N days" |

---

### POST /events/system-alert

Fire a system alert. Tenant-wide by default; set `user_id` to target a specific user.

**Request body:**

```json
{
  "title": "Scheduled Maintenance",
  "message": "Platform offline Sunday 02:00–04:00 UTC.",
  "user_id": null
}
```

---

## Utility Endpoints

### GET /health

Liveness probe. No authentication required.

**Response: 200 OK**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## HTTP Status Code Reference

| Status | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `400` | Bad request — domain validation error |
| `401` | Unauthorized — blank or missing X-Tenant-Id |
| `403` | Forbidden — notification exists but caller lacks permission |
| `404` | Not found — notification does not exist in this tenant |
| `422` | Unprocessable entity — missing required field or header |
| `500` | Internal server error |
