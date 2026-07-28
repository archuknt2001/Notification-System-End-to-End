<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/6271faed-0633-4acd-92f9-d8ca342d94d4" /># 🔔 Notification System End-to-End


## 👥 Team Members

| Name           | GitHub                      |
|----------------|---------|
| Archana Kumari | @archuknt2001 |
| Kashish Zehra  | @cipher-dev-04 |
| Muskan Perween | @muskanperweenmp0760-art |
| Nikee Kumari   | @nikee847422|

---

## 📖 Project Description
A full-stack, tenant-aware notification system that delivers real-time notifications to the right users based on application events. The system is designed to provide secure, reliable, and scalable notification management with a seamless user experience.

---

## 🎯 Objective
To build a secure and scalable notification system that enables real-time communication, improves user engagement, and ensures every notification reaches the intended user efficiently.

---


## 🏢 Organization
#Digitace Tech Solution
https://www.digitacetechsolutions.com/

---


## 🚀 Project Status
🚧 Developed

# AI-Native CRM Notification System

A production-ready, tenant-aware notification system built for AI-native CRM platforms used by Talent and Influencer Agencies.

---

## What this is

A full-stack notification module that plugs into any multi-tenant CRM. It demonstrates a complete notification pipeline:

```
Business Event → Notification Created → Stored → REST API → Frontend Bell → Unread Badge → Mark Read
```

It is designed to be extracted and embedded into a larger CRM codebase with minimal changes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Python 3.14 |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic v2 |
| Database | SQLite (swappable to PostgreSQL/MySQL via Alembic) |
| Migrations | Alembic |
| Frontend | React 19, Vite 6 |
| Styling | TailwindCSS 3 |
| HTTP Client | Axios |
| Testing | Pytest, FastAPI TestClient |

---

## Project Structure

```
notification-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── notifications.py   # 5 notification endpoints
│   │   │       └── events.py          # 8 event trigger endpoints
│   │   ├── core/
│   │   │   ├── config.py             # pydantic-settings configuration
│   │   │   ├── exceptions.py         # domain exception hierarchy
│   │   │   └── responses.py          # standard JSON envelope
│   │   ├── database/
│   │   │   ├── base.py               # SQLAlchemy DeclarativeBase
│   │   │   └── session.py            # engine, SessionLocal, get_db
│   │   ├── middleware/
│   │   │   └── context.py            # TenantContext + get_tenant_context
│   │   ├── models/
│   │   │   └── notification.py       # Notification ORM model
│   │   ├── repositories/
│   │   │   └── notification_repository.py  # all DB operations
│   │   ├── schemas/
│   │   │   └── notification_schema.py      # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── notification_service.py     # business logic
│   │   │   └── event_service.py            # business event triggers
│   │   └── utils/
│   │       └── pagination.py         # PaginationParams dependency
│   ├── alembic/                       # database migrations
│   ├── tests/                         # 112 pytest tests
│   ├── docs/                          # documentation
│   ├── main.py                        # FastAPI app factory
│   ├── seed.py                        # demo data seeder
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/               # Bell, Drawer, Card, Skeleton, FilterBar, DemoTrigger
│   │   ├── context/                  # NotificationContext (polling, state)
│   │   ├── hooks/                    # useNotifications (filtered list)
│   │   ├── services/                 # api.js (all HTTP calls)
│   │   └── utils/                    # relativeTime, notificationIcons
│   ├── App.jsx
│   └── package.json
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.12+ (tested on 3.14.2)
- Node.js 18+ (tested on 24.x)

### 1. Clone and enter the project

```bash
cd notification-system
```

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head

# Seed demo data (2 tenants, 20 notifications)
python seed.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API available at: http://localhost:8000
Interactive docs: http://localhost:8000/docs

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev
```

Frontend available at: http://localhost:5173

---

## Authentication

This system uses header-based identity for the demo:

| Header | Required | Description |
|---|---|---|
| `X-Tenant-Id` | Yes | Identifies the tenant for this request |
| `X-User-Id` | No | Identifies the user. Omit for tenant-wide operations |

All API calls enforce tenant isolation at the repository layer. A user cannot see, count, or modify notifications from another tenant — even by guessing IDs.

**JWT migration path:** Only `app/middleware/context.py::get_tenant_context` needs to change. All routes, services, and repositories are unchanged.

---

## Demo Identities (seed data)

| Identity | Tenant | User ID |
|---|---|---|
| Alice — Stellar Agency | `tenant-stellar-0001` | `user-alice-00000001` |
| Bob — Stellar Agency | `tenant-stellar-0001` | `user-bob-000000001` |
| Carol — Nova Co | `tenant-nova-00001` | `user-carol-0000001` |
| Dave — Nova Co | `tenant-nova-00001` | `user-dave-00000001` |

---

## API Endpoints

### Notifications

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/notifications` | Create a notification |
| `GET` | `/api/v1/notifications` | List visible notifications (paginated) |
| `GET` | `/api/v1/notifications/unread-count` | Unread count for bell badge |
| `PATCH` | `/api/v1/notifications/read-all` | Mark all visible as read |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark one notification as read |

### Events (demo triggers)

| Method | Path | Creates |
|---|---|---|
| `POST` | `/api/v1/events/member-invited` | Tenant-wide notification |
| `POST` | `/api/v1/events/creator-reply` | User-specific notification |
| `POST` | `/api/v1/events/campaign-started` | Tenant-wide notification |
| `POST` | `/api/v1/events/campaign-completed` | Tenant-wide notification |
| `POST` | `/api/v1/events/payment-received` | User-specific notification |
| `POST` | `/api/v1/events/report-ready` | User-specific notification |
| `POST` | `/api/v1/events/invoice-due` | User-specific notification |
| `POST` | `/api/v1/events/system-alert` | Tenant-wide or user-specific |

Full API documentation: see `docs/API_SPEC.md` or http://localhost:8000/docs

---

## Frontend Features

- Notification bell with animated unread badge (caps at 99+)
- Slide-in drawer with notification list
- Read/unread visual distinction (bold title, left border, dot)
- Click any card to mark it as read (optimistic update)
- Mark all read button
- Loading skeleton on initial fetch
- Empty state with illustration
- Relative timestamps ("2 minutes ago")
- Filter by notification type (11 types)
- Unread-only toggle
- Load more / pagination
- Polling every 20 seconds
- Demo event panel — fire any business event from the UI
- Tenant/user switcher — demonstrates strict isolation between tenants

---

## Running Tests

```bash
cd backend
venv\Scripts\activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific module
pytest tests/test_tenant_isolation.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

Current result: **112 passed, 0 failed**

---

## Seed Data

```bash
# Seed only if empty (default)
python seed.py

# Force re-seed (clears existing data)
python seed.py --force
```

Seed creates 20 notifications across 2 tenants, covering all 11 notification types, with a mix of tenant-wide and user-specific, read and unread.

---

## Environment Variables

Configured in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./notifications.db` | Database connection string |
| `APP_NAME` | `AI-Native CRM Notification System` | App title shown in /docs |
| `DEBUG` | `false` | Show internal error details in responses |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]` | CORS allowed origins (JSON array) |
| `DEFAULT_PAGE_SIZE` | `20` | Default pagination size |
| `MAX_PAGE_SIZE` | `100` | Maximum pagination size |

---

## Documentation

| Document | Description |
|---|---|
| `docs/ARCHITECTURE.md` | System design, layers, data flow |
| `docs/API_SPEC.md` | All endpoints with request/response examples |
| `docs/DATABASE_SCHEMA.md` | Model, indexes, business rules |
| `docs/TESTING.md` | Test strategy, how to run, coverage map |
| `docs/ASSUMPTIONS.md` | Design decisions and trade-offs |
| `docs/FUTURE_ENHANCEMENTS.md` | Roadmap and integration paths |
| `docs/implementation.md` | Phase-by-phase build log |
| `docs/brain.md` | Project vision and master reference |


## 🚀 Live Demo

**Live Website:** https://notification-system-end-to-end.vercel.app


