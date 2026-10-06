from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A containerized AI microservice powered by the **Gemini API** (free tier — 1500 req/day).\n\n"
        "All inference endpoints are **protected by JWT authentication**. "
        "Register → get a token → click the 🔓 Authorize button → use all AI endpoints.\n\n"
        "**Capabilities:** Text generation, Multi-turn chat, Text summarization, Multimodal image understanding."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health", tags=["Health"], summary="Service Health Check")
def health():
    """Returns service status and model configuration."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "model": settings.GEMINI_TEXT_MODEL,
        "vision_model": settings.GEMINI_VISION_MODEL,
    }

# Mount versioned API
app.include_router(api_router, prefix=settings.API_V1_STR)
