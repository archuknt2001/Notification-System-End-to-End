# Integration with Existing CRM

Current Challenge

Headers

↓

Notification API

Future Production

JWT Authentication

↓

User Service

↓

Event Bus (Kafka/RabbitMQ)

↓

Notification Service

↓

Database

↓

WebSocket Gateway

↓

Frontend

↓

Email Service

↓

Push Notifications

What remains unchanged:

- Notification Service
- Repository Layer
- Database Model
- Frontend UI

What changes:

- Replace header authentication with JWT.
- Replace manual triggers with domain events.
- Add WebSocket/SSE for real-time delivery.
- Integrate Email/Push providers.
