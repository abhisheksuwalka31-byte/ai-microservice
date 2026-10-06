import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func, select

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.logging import StructuredLoggingMiddleware
from app.api.v1 import api_router
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.inference_log import InferenceLog

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is ready
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A containerized AI microservice powered by the **Gemini API** with **RBAC (Role-Based Access Control)**, "
        "**SQLAlchemy 2.0 ORM**, **Alembic migrations**, **Audit Logging**, and **Structured Observability**.\n\n"
        "### Roles:\n"
        "- **admin**: Manage users, inspect system-wide audit logs, query telemetry.\n"
        "- **developer**: Execute all AI inference operations (text, chat, summarize, vision).\n"
        "- **viewer**: Read-only access to health, profile, and system metrics."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware: structured JSON logs + request correlation ID
app.add_middleware(StructuredLoggingMiddleware)

# Middleware: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root redirect to /docs so opening http://localhost:8000 directly loads the Swagger app
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# ── Observability Endpoints ───────────────────────────────────────────────────

@app.get("/health", tags=["Observability"], summary="Liveness Probe")
def health():
    """
    Kubernetes / Docker Liveness Probe:
    Fast response indicating the container process is alive and accepting traffic.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }


@app.get("/ready", tags=["Observability"], summary="Readiness Probe")
def readiness(response: Response, db: Session = Depends(get_db)):
    """
    Kubernetes / Docker Readiness Probe:
    Verifies database connectivity and API key readiness before routing live requests.
    """
    checks = {}
    is_ready = True

    # 1. Database connectivity check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        is_ready = False

    # 2. AI model provider readiness
    checks["ai_provider"] = "configured" if settings.GEMINI_API_KEY else "unconfigured (mock/test mode)"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": checks}

    return {"status": "ready", "checks": checks}


@app.get("/metrics", tags=["Observability"], summary="Service Telemetry & Metrics")
def metrics(db: Session = Depends(get_db)):
    """
    Returns high-level system usage, counts, and performance metrics.
    """
    total_users = db.execute(select(func.count(User.id))).scalar() or 0
    total_audit_events = db.execute(select(func.count(AuditLog.id))).scalar() or 0
    total_inferences = db.execute(select(func.count(InferenceLog.id))).scalar() or 0
    avg_latency = db.execute(select(func.avg(InferenceLog.latency_ms))).scalar() or 0.0

    return {
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "total_registered_users": total_users,
        "total_audit_events": total_audit_events,
        "total_ai_inferences": total_inferences,
        "average_inference_latency_ms": round(float(avg_latency), 2),
        "models": {
            "text": settings.GEMINI_TEXT_MODEL,
            "vision": settings.GEMINI_VISION_MODEL
        }
    }


# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)
