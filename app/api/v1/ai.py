from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
from app.api.deps import get_current_user
from app.schemas import TextRequest, ChatRequest, SummarizeRequest, AIResponse
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


# ── Text Generation ───────────────────────────────────────────────────────────

@router.post("/generate", response_model=AIResponse, summary="Generate Text")
def generate_text(
    payload: TextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    **Text Generation** — send a prompt and get an AI-generated response.

    - Supports optional `system_prompt` to set model behavior.
    - Supports `temperature` (0.0–2.0) and `max_tokens` controls.
    - **Requires JWT authentication.**
    """
    _check_gemini_key()
    try:
        return gemini.generate_text(
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Multi-turn Chat ───────────────────────────────────────────────────────────

@router.post("/chat", response_model=AIResponse, summary="Multi-turn Chat")
def chat(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    **Multi-turn Chat** — send a conversation history and receive the next assistant response.

    Messages must follow the format: `[{"role": "user", "content": "..."}, {"role": "model", "content": "..."}]`
    
    - Roles must alternate between `user` and `model`.
    - The last message must be from `user`.
    - **Requires JWT authentication.**
    """
    _check_gemini_key()
    messages = [m.model_dump() for m in payload.messages]

    # Validate: last message must be from user
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The last message in the conversation must be from role='user'."
        )

    try:
        return gemini.chat(
            messages=messages,
            system_prompt=payload.system_prompt,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Summarization ─────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=AIResponse, summary="Summarize Text")
def summarize(
    payload: SummarizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    **Summarization** — condense any text into a clean, structured summary.

    - `style`: `concise` (2–4 sentences), `detailed` (full coverage), `bullet` (key points as bullets).
    - Supports inputs up to 20,000 characters.
    - **Requires JWT authentication.**
    """
    _check_gemini_key()
    try:
        return gemini.summarize(text=payload.text, style=payload.style)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")


# ── Image Understanding ───────────────────────────────────────────────────────

@router.post("/analyze-image", response_model=AIResponse, summary="Analyze Image (Multimodal)")
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze (JPEG, PNG, WebP, GIF, BMP, TIFF)"),
    prompt: str = Form(default="Describe this image in detail.", description="Instruction for the model about what to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """
    **Image Understanding (Multimodal)** — upload any image and ask the AI anything about it.

    - Accepts: JPEG, PNG, WebP, GIF, BMP, TIFF images (max 20MB).
    - `prompt`: specify what to extract — description, text (OCR), objects, sentiment, code, etc.
    - **Requires JWT authentication.**

    **Example prompts:**
    - `"Describe this image in detail."`
    - `"What text is visible in this image?"`
    - `"List all objects you can identify."`
    - `"Is there any code in this image? If so, extract it."`
    """
    _check_gemini_key()

    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file must be smaller than 20MB."
        )

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        return gemini.analyze_image(
            image_bytes=image_bytes,
            mime_type=content_type,
            prompt=prompt
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini API error: {str(e)}")
