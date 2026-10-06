# 🤖 AI Microservice

A production-grade, containerized **FastAPI AI microservice** running open models via the **Gemini API free tier** (1,500 requests/day). Engineered with **Role-Based Access Control (RBAC)**, **SQLAlchemy 2.0 ORM & Alembic migrations**, **Audit Logging**, **zero N+1 queries**, **Structured JSON Observability**, and **GitHub Actions CI/CD**.

[![CI Pipeline](https://github.com/abhisheksuwalka31-byte/ai-microservice/actions/workflows/ci.yml/badge.svg)](https://github.com/abhisheksuwalka31-byte/ai-microservice/actions)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-purple.svg)](https://alembic.sqlalchemy.org)
[![Gemini](https://img.shields.io/badge/Gemini-Free%20Tier-orange.svg)](https://aistudio.google.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Key Architecture & SDLC Highlights

| Dimension | Engineering Implementation |
|---|---|
| 🔐 **RBAC Model** | Hierarchical roles (`admin`, `developer`, `viewer`) with granular dependency guards |
| 🗄️ **Database & Migrations** | SQLAlchemy 2.0 ORM with versioned Alembic migrations (`alembic upgrade head`) |
| ⚡ **N+1 Prevention** | `selectinload` eager loading on all relationships; batch aggregate queries |
| 📜 **Audit Logging** | Persistent audit trail recording user logins, registrations, and administrative events |
| 📊 **Observability** | Structured JSON logging with `X-Request-ID` correlation, `/health`, `/ready`, and `/metrics` |
| 🤖 **AI Capabilities** | Text generation, multi-turn chat, text summarization, multimodal image analysis |
| 🧪 **Test Suite** | 21 automated pytest tests covering RBAC, auth, input validation, and probes |
| 🔄 **DevOps & CI/CD** | Multi-stage Docker containerization and GitHub Actions automated pipeline |

---

## 🚀 Quick Start (Local Execution)

### 1. Clone the repository

```bash
git clone https://github.com/abhisheksuwalka31-byte/ai-microservice.git
cd ai-microservice
```

### 2. Set up virtual environment & install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment & run migrations

```bash
cp .env.example .env
alembic upgrade head
```

> 🆓 **Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)** (1,500 free requests/day). Add it to your `.env` file under `GEMINI_API_KEY`.

### 4. Run the microservice

```bash
python run.py
```

Open **`http://127.0.0.1:8000/docs`** for interactive Swagger UI documentation.

---

## 🐳 Docker Deployment

### Single-command Docker Compose

```bash
cp .env.example .env && nano .env
docker compose up --build
```

Access:
- Swagger Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Readiness check: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`

---

## 📡 API Reference & RBAC Permissions

### Observability Probes

| Endpoint | Method | Access | Purpose |
|---|---|---|---|
| `/health` | `GET` | Public | Liveness probe returning status & uptime |
| `/ready` | `GET` | Public | Readiness probe testing database connection |
| `/metrics` | `GET` | Public | Telemetry metrics: users, audit events, avg latency |

### Authentication & User Management

| Endpoint | Method | Role Required | Description |
|---|---|---|---|
| `/api/v1/auth/register` | `POST` | Public | Register user (`role`: `admin`, `developer`, or `viewer`) |
| `/api/v1/auth/token` | `POST` | Public | OAuth2 token endpoint for Swagger Authorize button |
| `/api/v1/auth/login` | `POST` | Public | JSON login endpoint |
| `/api/v1/auth/me` | `GET` | Any authenticated | Retrieve current user profile |
| `/api/v1/auth/users` | `GET` | **Admin Only** | List users with eager-loaded audit relations (no N+1) |
| `/api/v1/auth/audit-logs` | `GET` | **Admin Only** | Query system-wide security audit trail |

### AI Inference Endpoints

| Endpoint | Method | Role Required | Description |
|---|---|---|---|
| `/api/v1/ai/generate` | `POST` | **Developer / Admin** | Text generation with system instructions |
| `/api/v1/ai/chat` | `POST` | **Developer / Admin** | Multi-turn contextual conversation |
| `/api/v1/ai/summarize` | `POST` | **Developer / Admin** | Summarization (`concise`, `detailed`, `bullet`) |
| `/api/v1/ai/analyze-image` | `POST` | **Developer / Admin** | Multimodal vision & image understanding |
| `/api/v1/ai/logs` | `GET` | **Developer / Admin** | Inference latency & token consumption logs |

---

## 🧪 Testing & Quality Assurance

Run the automated test suite with coverage:

```bash
pytest -v --cov=app --cov-report=term-missing
```

**21 test cases verify**:
- Liveness, readiness, and metrics endpoints
- `X-Request-ID` correlation header generation
- User registration and duplicate constraint validation
- Password hashing & JWT token issuance
- RBAC permissions (`admin`, `developer`, `viewer` isolation)
- Prevention of N+1 queries during user and relationship listings
- AI endpoint auth guards and schema validation

---

## 📁 Repository Structure

```
ai-microservice/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI pipeline
├── alembic/
│   ├── versions/              # Migration history scripts
│   └── env.py                 # Alembic configuration
├── app/
│   ├── main.py                # FastAPI factory, probes, middleware
│   ├── schemas.py             # Pydantic v2 schemas
│   ├── core/
│   │   ├── config.py          # Pydantic BaseSettings
│   │   ├── database.py        # SQLAlchemy 2.0 engine & sessionmaker
│   │   ├── logging.py         # Structured JSON logging & correlation IDs
│   │   ├── security.py        # bcrypt & JWT security
│   │   └── users.py           # DB user queries with eager loading
│   ├── models/
│   │   ├── user.py            # User ORM model
│   │   ├── audit_log.py       # AuditLog ORM model
│   │   └── inference_log.py   # InferenceLog ORM model
│   ├── api/
│   │   ├── deps.py            # JWT & RBAC dependency guards
│   │   └── v1/
│   │       ├── auth.py        # Auth & admin endpoints
│   │       └── ai.py          # AI inference endpoints
│   └── services/
│       └── gemini.py          # Gemini API inference service
├── docs/
│   ├── ARCHITECTURE.md        # Technical architecture documentation
│   └── DEMO_SCRIPT.md         # 2-minute video recording script
├── tests/
│   └── test_main.py           # 21 automated pytest test cases
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── run.py
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE)
