import time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import require_role
from app.models.user import User, UserRole
from app.models.inference_log import InferenceLog
from app.schemas import TextRequest, ChatRequest, SummarizeRequest, AIResponse, InferenceLogResponse
from app.services import gemini

router = APIRouter()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp", "image/tiff"
}


def _check_gemini_key():
    from app.core.config import settings
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured. Set it in your .env file. Get one free at https://aistudio.google.com/apikey"
        )


def _record_inference(
    db: Session,
    user_id: int,
    endpoint: str,
    response_data: dict,
    latency_ms: float
):
    usage = response_data.get("usage") or {}
    log_entry = InferenceLog(
        user_id=user_id,
        endpoint=endpoint,
        model_name=response_data.get("model", "gemini-2.0-flash"),
        prompt_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("output_tokens"),
        latency_ms=round(latency_ms, 2)
    )
    db.add(log_entry)
    db.commit()


# ── Text Generation ───────────────────────────────────────────────────────────

@router.post("/generate", response_model=AIResponse, summary="Generate Text (Admin/Developer)")
def generate_text(
    payload: TextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
):
    """
    **Text Generation** — send a prompt and get an AI-generated response.
    - RBAC: Allowed for `admin` and `developer` roles.
    - Records inference latency and token counts into database.
    """
    _check_gemini_key()
    start = time.perf_counter()
    try:
        result = gemini.generate_text(
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        latency_ms = (time.perf_counter() - start) * 1000
        _record_inference(db, current_user.id, "/generate", result, latency_ms)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Multi-turn Chat ───────────────────────────────────────────────────────────

@router.post("/chat", response_model=AIResponse, summary="Multi-turn Chat (Admin/Developer)")
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
):
    """
    **Multi-turn Chat** — send conversation history and receive the next assistant response.
    - RBAC: Allowed for `admin` and `developer` roles.
    """
    _check_gemini_key()
    messages = [m.model_dump() for m in payload.messages]

    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The last message in the conversation must be from role='user'."
        )

    start = time.perf_counter()
    try:
        result = gemini.chat(
            messages=messages,
            system_prompt=payload.system_prompt,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        latency_ms = (time.perf_counter() - start) * 1000
        _record_inference(db, current_user.id, "/chat", result, latency_ms)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Summarization ─────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=AIResponse, summary="Summarize Text (Admin/Developer)")
def summarize(
    payload: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
):
    """
    **Summarization** — condense any text into a clean summary.
    - RBAC: Allowed for `admin` and `developer` roles.
    """
    _check_gemini_key()
    start = time.perf_counter()
    try:
        result = gemini.summarize(text=payload.text, style=payload.style)
        latency_ms = (time.perf_counter() - start) * 1000
        _record_inference(db, current_user.id, "/summarize", result, latency_ms)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Image Understanding ───────────────────────────────────────────────────────

@router.post("/analyze-image", response_model=AIResponse, summary="Analyze Image (Admin/Developer)")
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze (JPEG, PNG, WebP, GIF, BMP, TIFF)"),
    prompt: str = Form(default="Describe this image in detail.", description="Instruction for the model"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
):
    """
    **Image Understanding (Multimodal)** — upload an image and query the model.
    - RBAC: Allowed for `admin` and `developer` roles.
    """
    _check_gemini_key()

    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file must be smaller than 20MB."
        )

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    start = time.perf_counter()
    try:
        result = gemini.analyze_image(
            image_bytes=image_bytes,
            mime_type=content_type,
            prompt=prompt
        )
        latency_ms = (time.perf_counter() - start) * 1000
        _record_inference(db, current_user.id, "/analyze-image", result, latency_ms)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Observability & Usage Logs ────────────────────────────────────────────────

@router.get("/logs", response_model=List[InferenceLogResponse], summary="Get Inference Logs (Admin/Developer)")
def get_inference_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
):
    """
    Retrieve recent inference metrics (latency, tokens, endpoint) for the user or system.
    """
    stmt = select(InferenceLog)
    if current_user.role != UserRole.ADMIN.value:
        stmt = stmt.where(InferenceLog.user_id == current_user.id)

    stmt = stmt.order_by(InferenceLog.created_at.desc()).offset(skip).limit(limit)
    logs = db.execute(stmt).scalars().all()
    return [InferenceLogResponse.model_validate(log) for log in logs]
