# AI-Native CRM Notification System
## Master Project Brain

Version: 1.0

---

# 1. Project Vision

Build a production-ready, tenant-aware Notification System that can integrate into an existing AI-native CRM used by Talent/Influencer Agencies.

The system should provide a complete notification pipeline:

Event Happens
↓

Notification Created

↓

Stored in Database

↓

Visible to Correct User

↓

Unread Count Updated

↓

User Reads Notification

↓

Notification Status Updated

The project should demonstrate proper software engineering practices including clean architecture, multi-tenancy, REST APIs, frontend integration, testing, and documentation.

---

# 2. Objectives

The system must:

- Support multiple tenants
- Prevent cross-tenant access
- Provide REST APIs
- Trigger notifications automatically
- Display notifications in frontend
- Poll for new notifications
- Mark notifications as read
- Mark all notifications as read
- Display unread badge
- Be scalable for future event-driven architecture

---

# 3. Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- SQLite (or MySQL)
- Repository Pattern

## Frontend

- React
- Vite
- TailwindCSS
- Axios
- React Context

## Testing

- Pytest
- HTTPX

---

# 4. Architecture

Client

↓

REST API

↓

FastAPI Controllers

↓

Service Layer

↓

Repository Layer

↓

Database

---

# 5. Folder Structure

notification-system/

backend/

app/

api/

middleware/

models/

schemas/

services/

repositories/

database/

core/

utils/

seed.py

main.py

frontend/

src/

components/

pages/

hooks/

services/

layouts/

assets/

utils/

tests/

README.md

BRAIN.md

IMPLEMENTATION.md

INTEGRATION.md

CHANGELOG.md

---

# 6. Notification Model

Notification

id

tenantId

userId

type

title

body

read

createdAt

readAt

Rules

tenantId

Required

userId

Nullable

If NULL

Visible to everyone in tenant

Otherwise

Visible only to specified user

---

# 7. Authentication

Current Challenge

Headers

X-Tenant-Id

X-User-Id

Treat headers as trusted identity.

Production

JWT Authentication

↓

Middleware

↓

Extract Tenant & User

↓

Authorization

---

# 8. API Endpoints

POST /notifications

Create Notification

GET /notifications

List Notifications

Unread First

Newest First

Pagination

GET /notifications/unread-count

Unread Badge

PATCH /notifications/{id}/read

Mark Single Read

PATCH /notifications/read-all

Mark All Read

---

# 9. Business Rules

Tenant isolation is mandatory.

Users must never:

View another tenant's notification.

Count another tenant's notification.

Mark another tenant's notification.

Even by guessing IDs.

---

# 10. Notification Types

member_invited

new_reply

report_ready

deal_won

payment_received

invoice_due

campaign_started

campaign_completed

system_alert

warning

success

error

---

# 11. Notification Lifecycle

Business Event

↓

NotificationService

↓

Repository

↓

Database

↓

API

↓

Frontend Poll

↓

Bell Badge

↓

Notification Drawer

↓

User Reads

↓

Database Updated

---

# 12. Trigger System

Trigger 1

Invite Team Member

↓

Create Tenant-wide Notification

Trigger 2

Creator Reply

↓

Create User Notification

Both triggers must use

NotificationService

Never directly access repository.

---

# 13. Frontend

Landing Page

↓

Notification Bell

↓

Unread Badge

↓

Notification Drawer

↓

Notification Cards

↓

Read

↓

Mark All Read

---

# 14. UI Components

NotificationBell

NotificationBadge

NotificationDrawer

NotificationCard

NotificationList

NotificationFilter

EmptyState

LoadingSkeleton

Toast

---

# 15. Features

Unread Badge

Pagination

Relative Time

Mark Read

Mark All Read

Unread Highlight

Polling

Search

Filters

Responsive UI

Dark Mode Ready

---

# 16. Notification Filters

All

Unread

Member Invites

Replies

Reports

Payments

Alerts

---

# 17. Relative Time

Examples

Now

5 minutes ago

1 hour ago

Yesterday

3 days ago

---

# 18. Polling

Frontend polls

Every 20 seconds

Endpoints

GET /notifications

GET /notifications/unread-count

---

# 19. Service Layer

NotificationService

Create

Read

ReadAll

CountUnread

ListNotifications

EventService

InviteMember()

CreatorReply()

GenerateReport()

---

# 20. Repository Layer

NotificationRepository

create()

findVisible()

findById()

countUnread()

markRead()

markAllRead()

---

# 21. Database Rules

Index

tenantId

userId

read

createdAt

Composite Index

tenantId + userId

---

# 22. Security

Header Authentication

Tenant Isolation

Input Validation

Soft Delete Ready

Repository Pattern

No Raw SQL

Prepared Statements

Rate Limiting Ready

Audit Logging Ready

---

# 23. Error Handling

400

Bad Request

401

Unauthorized

403

Forbidden

404

Not Found

500

Internal Server Error

---

# 24. Testing

Tenant Isolation

Unread Count

Pagination

Sorting

Mark Read

Mark All Read

Wrong Tenant Access

Trigger Tests

Repository Tests

Service Tests

---

# 25. Integration Plan

Current

Headers

↓

REST API

Future

JWT

↓

Event Bus

↓

Notification Service

↓

WebSocket

↓

Email

↓

Push Notification

---

# 26. Future Enhancements

WebSocket

Redis Cache

Kafka

RabbitMQ

Email Notifications

Push Notifications

Notification Preferences

Archive Notifications

Delete Notifications

Scheduled Notifications

Slack Integration

Microsoft Teams Integration

---

# 27. Coding Standards

Clean Architecture

Repository Pattern

SOLID Principles

Reusable Components

Typed APIs

Dependency Injection

Proper Exception Handling

Reusable Services

Consistent Response Format

---

# 28. AI Instructions

Treat this file as the project's single source of truth.

Always:

Read BRAIN.md first.

Follow Clean Architecture.

Never bypass NotificationService.

Never bypass Repository Layer.

Maintain Tenant Isolation.

Write scalable code.

Write production-ready code.

Generate reusable components.

Write tests.

Keep documentation updated.
