# 🤖 AI Microservice

A **containerized FastAPI microservice** powered by the **Gemini API (free tier)** with JWT authentication and Pydantic v2 schema validation.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-Free%20Tier-orange.svg)](https://aistudio.google.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Capability | Description |
|---|---|
| 🔐 **JWT Authentication** | Register → receive token → access all AI endpoints |
| 📝 **Text Generation** | Send any prompt and receive AI-generated text |
| 💬 **Multi-turn Chat** | Full conversation history with context retention |
| 📋 **Text Summarization** | Concise, detailed, or bullet-point summaries |
| 🖼️ **Image Understanding** | Upload any image and ask anything about it (multimodal) |
| 🐳 **Docker Ready** | Single `docker compose up` to run everything |
| 📖 **Interactive Docs** | Auto-generated Swagger UI at `/docs` |

---

## 🚀 Quick Start (Local)

### 1. Clone the repository

```bash
git clone https://github.com/abhisheksuwalka31-byte/ai-microservice.git
cd ai-microservice
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_key_here
```

> 🆓 **Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)**  
> Free tier: **1,500 requests/day** — no credit card required.

### 4. Run the server

```bash
python run.py
```

Open **http://127.0.0.1:8000/docs** — the interactive Swagger UI.

---

## 🐳 Docker Setup

### Using Docker Compose (recommended)

```bash
# 1. Add your API key to .env first
cp .env.example .env && nano .env

# 2. Build and start
docker compose up --build

# 3. Access at
http://localhost:8000/docs
```

### Using Docker directly

```bash
docker build -t ai-microservice .
docker run -p 8000:8000 --env-file .env ai-microservice
```

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user → returns JWT token |
| `POST` | `/api/v1/auth/token` | Login (OAuth2 form) — for Swagger Authorize button |
| `POST` | `/api/v1/auth/login` | Login (JSON body) |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### AI Inference (all require JWT)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/ai/generate` | Text generation |
| `POST` | `/api/v1/ai/chat` | Multi-turn conversation |
| `POST` | `/api/v1/ai/summarize` | Text summarization |
| `POST` | `/api/v1/ai/analyze-image` | Multimodal image understanding |
| `GET` | `/health` | Service health check |

### Example: Register + Generate Text

```bash
# Step 1: Register
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"pass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Step 2: Generate text
curl -X POST http://localhost:8000/api/v1/ai/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in 3 sentences."}'
```

### Example: Analyze an Image

```bash
curl -X POST http://localhost:8000/api/v1/ai/analyze-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/image.jpg" \
  -F "prompt=What objects are visible in this image?"
```

---

## 🏗️ Architecture

```
ai-microservice/
├── app/
│   ├── main.py              # FastAPI app + CORS + router mounting
│   ├── schemas.py           # Pydantic v2 models (request/response)
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── security.py      # bcrypt hashing + JWT encode/decode
│   │   └── users.py         # In-memory user store
│   ├── api/
│   │   ├── deps.py          # JWT authentication dependency
│   │   └── v1/
│   │       ├── auth.py      # Auth endpoints
│   │       └── ai.py        # AI inference endpoints
│   └── services/
│       └── gemini.py        # Gemini API wrapper (text, chat, summarize, vision)
├── tests/
│   └── test_main.py         # 14 pytest tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.py                   # Local development server
└── .env.example
```

**Flow:**
```
Client → FastAPI → JWT Middleware → AI Endpoint → Gemini Service → Gemini API
```

---

## 🧪 Running Tests

```bash
source venv/bin/activate
pytest -v
```

Tests cover: health check, user registration, duplicate detection, login, profile, auth guards on all AI endpoints, and input validation.

---

## 🔐 Security

- All AI inference endpoints require a valid **JWT Bearer token**
- Passwords are hashed with **bcrypt** (cost factor 12)
- Tokens expire in 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- CORS is enabled — restrict `allow_origins` in production
- `SECRET_KEY` must be changed from the default for production deployments

---

## 📜 License

MIT License — see [LICENSE](LICENSE)
