# System Architecture & Technical Documentation

## 1. System Overview

This microservice provides a containerized, production-grade AI gateway wrapping the **Gemini API** (free tier — 1,500 requests/day). It implements enterprise architectural standards directly addressing modern production requirements:

- **Role-Based Access Control (RBAC)**: Distinct permissions for `admin`, `developer`, and `viewer`.
- **Database Persistence & Migrations**: SQLAlchemy 2.0 ORM backed by Alembic versioned migrations.
- **Eager Loading Optimization**: Zero N+1 queries through SQLAlchemy `selectinload` relationship strategies.
- **Security & Audit Logging**: Cryptographically hashed passwords (bcrypt), JWT tokens, and persistent audit logs for all sensitive actions.
- **Full Observability & DevOps**: Structured JSON logging, request correlation IDs (`X-Request-ID`), Kubernetes-compliant `/health` and `/ready` probes, `/metrics` endpoint, and automated GitHub Actions CI pipeline.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                                CLIENT                                  │
│               (cURL, Swagger UI /docs, Frontend, Postman)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Requests (with X-Request-ID)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                            │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    StructuredLoggingMiddleware                    │  │
│  │    • Injects UUID X-Request-ID Header                            │  │
│  │    • Emits structured JSON logs (latency, status, path, client)  │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │                     Observability Layer                          │  │
│  │    GET /health   → Liveness probe (uptime, status)               │  │
│  │    GET /ready    → Readiness probe (DB ping + provider check)    │  │
│  │    GET /metrics  → Operational metrics (counts, avg latency)    │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │                       API Routing & RBAC                         │  │
│  │                                                                  │  │
│  │   /api/v1/auth/*                                                 │  │
│  │     POST /register    [Public]   → Hash pass + issue JWT + Audit │  │
│  │     POST /token       [Public]   → OAuth2 Form login (Swagger)   │  │
│  │     POST /login       [Public]   → JSON login + Audit            │  │
│  │     GET  /me          [Bearer]   → Self profile                  │  │
│  │     GET  /users       [Admin]    → Eager-loaded user list        │  │
│  │     GET  /audit-logs  [Admin]    → System audit trail            │  │
│  │                                                                  │  │
│  │   /api/v1/ai/*                                                   │  │
│  │     POST /generate    [Dev/Admin] → Text generation + telemetry  │  │
│  │     POST /chat        [Dev/Admin] → Multi-turn context + usage   │  │
│  │     POST /summarize   [Dev/Admin] → Multi-style summary          │  │
│  │     POST /analyze-img [Dev/Admin] → Multimodal vision analysis   │  │
│  │     GET  /logs        [Dev/Admin] → Inference telemetry log      │  │
│  └───────────────┬──────────────────────────────────┬───────────────┘  │
└──────────────────┼──────────────────────────────────┼──────────────────┘
                   │                                  │
                   ▼                                  ▼
      ┌────────────────────────┐         ┌─────────────────────────┐
      │  SQLAlchemy 2.0 ORM    │         │     Gemini API          │
      │  + Alembic Migrations  │         │     (Free Tier)         │
      │                        │         │                         │
      │  • users (indexed)     │         │   gemini-2.0-flash      │
      │  • audit_logs (indexed)│         │   1,500 req/day         │
      │  • inference_logs      │         └─────────────────────────┘
      └────────────────────────┘
```

---

## 3. Role-Based Access Control (RBAC) Model

| Role | Health / Metrics | Auth / Profile | AI Inference (`/ai/*`) | Admin Operations (`/users`, `/audit-logs`) |
| :--- | :---: | :---: | :---: | :---: |
| **`viewer`** | ✅ Allowed | ✅ Allowed | ❌ 403 Forbidden | ❌ 403 Forbidden |
| **`developer`** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ❌ 403 Forbidden |
| **`admin`** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ Allowed |

Roles are enforced using FastAPI's dependency injection (`require_role(UserRole.ADMIN, ...)`).

---

## 4. Database Schema & Elimination of N+1 Queries

### Schema Design & Indexing
- **`users`**: `id` (PK, indexed), `username` (unique, indexed), `email` (unique, indexed), `role` (indexed), `hashed_password`, `is_active`, `created_at`.
- **`audit_logs`**: `id` (PK, indexed), `user_id` (FK to `users.id`, indexed), `action` (indexed), `resource`, `ip_address`, `status_code`, `created_at` (indexed).
- **`inference_logs`**: `id` (PK, indexed), `user_id` (FK to `users.id`, indexed), `endpoint` (indexed), `model_name`, `prompt_tokens`, `output_tokens`, `latency_ms`, `created_at` (indexed).

### Eager Loading Strategy
To prevent N+1 query antipatterns where related child records are queried in loops:
```python
# app/core/users.py
stmt = (
    select(User)
    .options(selectinload(User.audit_logs), selectinload(User.inference_logs))
    .offset(skip)
    .limit(limit)
)
```
SQLAlchemy issues an optimized batch `IN (...)` load query rather than executing N individual child queries.

---

## 5. Observability & DevOps

### Structured JSON Logging
Every request emits structured JSON with request correlation:
```json
{
  "timestamp": "2026-10-06 19:13:47",
  "level": "INFO",
  "logger": "ai_microservice",
  "message": "POST /api/v1/auth/register HTTP/1.1 201 - 7.22ms",
  "request_id": "59b27c0d-4eee-400b-a5c8-c4f10e78d8f9",
  "path": "/api/v1/auth/register",
  "status_code": 201,
  "duration_ms": 7.22
}
```

### Probes & Telemetry
- **`/health`**: Liveness probe returning status, uptime, service version.
- **`/ready`**: Readiness probe executing a `SELECT 1` database query and verifying provider configuration.
- **`/metrics`**: Aggregates user counts, audit events, inference counts, and average inference latency.

### CI/CD Pipeline (`.github/workflows/ci.yml`)
- Automates Python 3.12 environment setup.
- Verifies Alembic database migration validity via `alembic upgrade head`.
- Runs the test suite via `pytest -v --cov=app --cov-fail-under=80`.
- Builds Docker image container to verify deployability.
