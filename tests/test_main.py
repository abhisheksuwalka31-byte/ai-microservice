import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(username="testuser", email="test@example.com", password="secret123"):
    return client.post("/api/v1/auth/register", json={
        "username": username, "email": email, "password": password
    })


def get_token(username="testuser", password="secret123"):
    response = register_user(username, email=f"{username}@example.com", password=password)
    if response.status_code != 201:
        # Already registered, log in via form
        resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
        return resp.json()["access_token"]
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth Tests ────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "model" in data


def test_register_success():
    r = client.post("/api/v1/auth/register", json={
        "username": "newuser99",
        "email": "newuser99@example.com",
        "password": "password123"
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["user"]["username"] == "newuser99"


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


# ── AI Endpoints: Auth Guard Tests (no real API key needed) ───────────────────

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
    assert r.status_code in (401, 422)  # 401 or 422 if missing file


def test_generate_text_no_key_returns_503():
    """When GEMINI_API_KEY is unconfigured, endpoint returns 503 with a helpful message."""
    token = get_token("keytest_user", "keytest123")
    r = client.post(
        "/api/v1/ai/generate",
        json={"prompt": "Hello world"},
        headers=auth_headers(token)
    )
    # Either 503 (no key configured) or 200 (key configured in env)
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        assert "GEMINI_API_KEY" in r.json()["detail"]


def test_chat_last_message_must_be_user():
    """Chat endpoint validates that conversation ends with user message."""
    token = get_token("chatvaliduser", "chatpass99")
    r = client.post(
        "/api/v1/ai/chat",
        json={"messages": [{"role": "user", "content": "Hi"}, {"role": "model", "content": "Hello!"}]},
        headers=auth_headers(token)
    )
    # Expect 422 (validation error) because last message is from model
    assert r.status_code in (422, 503)


def test_summarize_invalid_style():
    token = get_token("styleuser", "stylepass99")
    r = client.post(
        "/api/v1/ai/summarize",
        json={"text": "Some text here.", "style": "invalid_style"},
        headers=auth_headers(token)
    )
    assert r.status_code == 422
