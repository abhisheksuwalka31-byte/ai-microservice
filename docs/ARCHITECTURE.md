# System Architecture & Technical Documentation

## Overview

This microservice exposes a **versioned REST API** that wraps the Gemini API with JWT-protected endpoints for text generation, multi-turn chat, summarization, and multimodal image understanding. It is containerized via Docker and runnable both locally and in any container orchestration platform.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENT                              │
│         (curl / Swagger UI / SDK / Application)          │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/HTTPS
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                                                          │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │  /health     │    │     CORS Middleware           │   │
│  │  GET         │    │  (cross-origin support)       │   │
│  └──────────────┘    └──────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │            /api/v1/auth/*                        │    │
│  │                                                  │    │
│  │  POST /register   →  Create user + issue JWT     │    │
│  │  POST /token      →  OAuth2 login (Swagger)      │    │
│  │  POST /login      →  JSON login                  │    │
│  │  GET  /me         →  Profile (JWT required)      │    │
│  └────────────────────────┬────────────────────────┘    │
│                           │                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │            /api/v1/ai/*  (JWT Required)          │    │
│  │                                                  │    │
│  │  POST /generate      →  Text Generation          │    │
│  │  POST /chat          →  Multi-turn Chat          │    │
│  │  POST /summarize     →  Summarization            │    │
│  │  POST /analyze-image →  Image Understanding      │    │
│  └────────────────────────┬────────────────────────┘    │
└───────────────────────────┼─────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Gemini API    │
                    │  (Free Tier)   │
                    │                │
                    │  gemini-3.8-   │
                    │  flash model   │
                    └────────────────┘
```

---

## Component Breakdown

### `app/main.py`
- FastAPI app factory
- CORS middleware (all origins allowed — restrict for production)
- Lifespan context manager
- Mounts `/api/v1` router and `/health` endpoint

### `app/core/config.py`
- `pydantic-settings` `BaseSettings` — reads from `.env` file
- Central source of truth for `SECRET_KEY`, `GEMINI_API_KEY`, model names, token TTL

### `app/core/security.py`
- `bcrypt` password hashing (bcrypt.gensalt → bcrypt.hashpw)
- JWT encode/decode via `python-jose` with HS256 algorithm
- `create_access_token(subject)` → signed JWT string

### `app/core/users.py`
- Thread-safe in-memory user dictionary (demo only)
- `create_user`, `get_user_by_username`, `get_user_by_id`, `authenticate_user`
- Production: replace with PostgreSQL via SQLAlchemy

### `app/api/deps.py`
- `get_current_user` FastAPI dependency
- Reads `Authorization: Bearer <token>` header
- Decodes JWT → fetches user → raises 401 if invalid

### `app/schemas.py`
- All Pydantic v2 models (input validation + response serialization)
- `UserRegisterRequest`, `Token`, `UserResponse`
- `TextRequest`, `ChatRequest`, `SummarizeRequest`, `AIResponse`

### `app/api/v1/auth.py`
- `/register` — creates user, returns token
- `/token` — OAuth2 form login (Swagger UI compatible)
- `/login` — JSON login
- `/me` — authenticated user profile

### `app/api/v1/ai.py`
- All AI inference endpoints
- Each endpoint validates auth → checks API key → calls service layer → returns `AIResponse`

### `app/services/gemini.py`
- Singleton `google.genai.Client` (lazy init on first call)
- `generate_text(prompt, system_prompt, temperature, max_tokens)`
- `chat(messages, system_prompt, temperature, max_tokens)`
- `summarize(text, style)` — wraps `generate_text` with system prompt
- `analyze_image(image_bytes, mime_type, prompt)` — multimodal via `Part.from_bytes`

---

## API Contracts

### `POST /api/v1/auth/register`
```json
// Request
{ "username": "alice", "email": "alice@example.com", "password": "secret123" }

// Response 201
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "alice", "email": "alice@example.com", "created_at": "..." }
}
```

### `POST /api/v1/ai/generate`
```json
// Request (Authorization: Bearer <token>)
{
  "prompt": "Explain quantum computing.",
  "system_prompt": "You are a physics professor.",
  "temperature": 0.7,
  "max_tokens": 500
}

// Response 200
{
  "result": "Quantum computing uses quantum bits...",
  "model": "gemini-3.8-flash",
  "usage": { "prompt_tokens": 12, "output_tokens": 97, "total_tokens": 109 }
}
```

### `POST /api/v1/ai/chat`
```json
// Request
{
  "messages": [
    { "role": "user", "content": "Hello, my name is Alice." },
    { "role": "model", "content": "Hello Alice! How can I help?" },
    { "role": "user", "content": "What's my name?" }
  ]
}

// Response 200
{ "result": "Your name is Alice.", "model": "gemini-3.8-flash", "usage": {...} }
```

### `POST /api/v1/ai/summarize`
```json
// Request
{ "text": "Long article text here...", "style": "bullet" }
// Styles: "concise" | "detailed" | "bullet"
```

### `POST /api/v1/ai/analyze-image`
```
// multipart/form-data
file: <image file>  (JPEG, PNG, WebP, GIF, BMP, TIFF — max 20MB)
prompt: "What is in this image?"

// Response 200
{ "result": "The image shows a cat sitting on a...", "model": "gemini-3.8-flash", "usage": {...} }
```

---

## Security Model

| Concern | Implementation |
|---|---|
| Password storage | bcrypt (adaptive, no plain text ever stored) |
| Authentication | JWT HS256, 60-min expiry |
| API key exposure | Stored only in `.env` (never committed) |
| Input validation | Pydantic v2 validates all request bodies before handler |
| File upload safety | Content-type allowlist, 20MB hard limit |
| CORS | Configurable — restrict `allow_origins` for production |

---

## Model Configuration

| Setting | Default | Description |
|---|---|---|
| `GEMINI_TEXT_MODEL` | `gemini-3.8-flash` | Used for text, chat, summarization |
| `GEMINI_VISION_MODEL` | `gemini-3.8-flash` | Used for image understanding |

> Update via `.env` to switch models without code changes.

---

## Running Tests

```bash
pytest -v
# 14 tests — covers: health, auth CRUD, duplicate guard, login, JWT validation,
# AI endpoint auth guards, input validation, style validation
```
