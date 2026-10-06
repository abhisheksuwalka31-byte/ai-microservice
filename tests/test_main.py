import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

# Isolated In-Memory SQLite database specifically for tests so app.db is never touched
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables in-memory before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(username="testuser", email="test@example.com", password="secret123", role="developer"):
    return client.post("/api/v1/auth/register", json={
        "username": username, "email": email, "password": password, "role": role
    })


def get_token(username="testuser", password="secret123", role="developer"):
    response = register_user(username, email=f"{username}@example.com", password=password, role=role)
    if response.status_code == 201:
        return response.json()["access_token"]
    resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health & Observability Tests ──────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data


def test_readiness_probe():
    r = client.get("/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "connected"


def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "uptime_seconds" in data
    assert "total_registered_users" in data
    assert "total_audit_events" in data
    assert "average_inference_latency_ms" in data


def test_request_correlation_id_header():
    r = client.get("/health")
    assert "x-request-id" in r.headers
    custom_id = "test-req-uuid-12345"
    r2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert r2.headers["x-request-id"] == custom_id


# ── Auth Tests ────────────────────────────────────────────────────────────────

def test_register_success():
    r = client.post("/api/v1/auth/register", json={
        "username": "newuser99",
        "email": "newuser99@example.com",
        "password": "password123",
        "role": "developer"
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["user"]["username"] == "newuser99"
    assert data["user"]["role"] == "developer"


def test_register_duplicate_username():
    client.post("/api/v1/auth/register", json={
        "username": "dupuser", "email": "dup@example.com", "password": "pass123"
    })
    r = client.post("/api/v1/auth/register", json={
        "username": "dupuser", "email": "dup2@example.com", "password": "pass123"
    })
    assert r.status_code == 400
    assert "already taken" in r.json()["detail"].lower()


def test_login_via_token_endpoint():
    client.post("/api/v1/auth/register", json={
        "username": "loginuser", "email": "login@example.com", "password": "mypass99"
    })
    r = client.post("/api/v1/auth/token", data={"username": "loginuser", "password": "mypass99"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_invalid_credentials():
    r = client.post("/api/v1/auth/token", data={"username": "nobody", "password": "wrong"})
    assert r.status_code == 401


def test_get_me_authenticated():
    r = register_user("meuser", "meuser@example.com", "pass123")
    token = r.json()["access_token"]
    r2 = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert r2.status_code == 200
    assert r2.json()["username"] == "meuser"


def test_get_me_unauthenticated():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── RBAC Tests ────────────────────────────────────────────────────────────────

def test_admin_can_list_users_with_eager_loading():
    admin_token = get_token("superadmin", "admin123", role="admin")
    r = client.get("/api/v1/auth/users", headers=auth_headers(admin_token))
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    for u in users:
        assert "audit_logs" in u
        assert "inference_logs" in u


def test_non_admin_cannot_list_users():
    dev_token = get_token("regulardev", "dev123", role="developer")
    r = client.get("/api/v1/auth/users", headers=auth_headers(dev_token))
    assert r.status_code == 403
    assert "Operation not permitted" in r.json()["detail"]


def test_admin_can_view_audit_trail():
    admin_token = get_token("auditadmin", "admin123", role="admin")
    r = client.get("/api/v1/auth/audit-logs", headers=auth_headers(admin_token))
    assert r.status_code == 200
    logs = r.json()
    assert isinstance(logs, list)
    assert len(logs) > 0


def test_viewer_role_cannot_call_inference():
    viewer_token = get_token("viewer1", "viewer123", role="viewer")
    r = client.post(
        "/api/v1/ai/generate",
        json={"prompt": "Hello"},
        headers=auth_headers(viewer_token)
    )
    assert r.status_code == 403
    assert "Operation not permitted" in r.json()["detail"]


# ── AI Endpoints: Auth Guard Tests ────────────────────────────────────────────

def test_generate_text_requires_auth():
    r = client.post("/api/v1/ai/generate", json={"prompt": "Hello"})
    assert r.status_code == 401


def test_chat_requires_auth():
    r = client.post("/api/v1/ai/chat", json={"messages": [{"role": "user", "content": "Hi"}]})
    assert r.status_code == 401


def test_summarize_requires_auth():
    r = client.post("/api/v1/ai/summarize", json={"text": "Some text to summarize.", "style": "concise"})
    assert r.status_code == 401


def test_analyze_image_requires_auth():
    r = client.post("/api/v1/ai/analyze-image")
    assert r.status_code in (401, 422)


def test_generate_text_no_key_returns_503_for_dev_role():
    token = get_token("keytest_user", "keytest123", role="developer")
    r = client.post(
        "/api/v1/ai/generate",
        json={"prompt": "Hello world"},
        headers=auth_headers(token)
    )
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        assert "GEMINI_API_KEY" in r.json()["detail"]


def test_chat_last_message_must_be_user():
    token = get_token("chatvaliduser", "chatpass99", role="developer")
    r = client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "Hi"}, {"role": "model", "content": "Hello!"}]},
        headers=auth_headers(token)
    )
    assert r.status_code in (422, 503)


def test_summarize_invalid_style():
    token = get_token("styleuser", "stylepass99", role="developer")
    r = client.post(
        "/api/v1/ai/summarize",
        json={"text": "Some text here.", "style": "invalid_style"},
        headers=auth_headers(token)
    )
    assert r.status_code == 422
