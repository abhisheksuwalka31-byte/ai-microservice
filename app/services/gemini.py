"""
Gemini AI service layer.
Uses google-genai SDK (>= 2.3.0) with client.models.generate_content.
Supports text generation, multi-turn chat, text summarization, and image understanding.
"""
import base64
from typing import Optional
from google import genai
from google.genai import types

from app.core.config import settings

# Lazy singleton client
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _make_config(
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> types.GenerateContentConfig:
    kwargs = {}
    if system_prompt:
        kwargs["system_instruction"] = system_prompt
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_output_tokens"] = max_tokens
    return types.GenerateContentConfig(**kwargs) if kwargs else None


# ── Text Generation ───────────────────────────────────────────────────────────

def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    client = get_client()
    config = _make_config(system_prompt, temperature, max_tokens)

    kwargs = dict(
        model=settings.GEMINI_TEXT_MODEL,
        contents=prompt,
    )
    if config:
        kwargs["config"] = config

    response = client.models.generate_content(**kwargs)

    usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        m = response.usage_metadata
        usage = {
            "prompt_tokens": getattr(m, "prompt_token_count", None),
            "output_tokens": getattr(m, "candidates_token_count", None),
            "total_tokens": getattr(m, "total_token_count", None),
        }

    return {"result": response.text, "model": settings.GEMINI_TEXT_MODEL, "usage": usage}


# ── Multi-turn Chat ───────────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    client = get_client()
    config = _make_config(system_prompt, temperature, max_tokens)

    contents = [
        types.Content(
            role=m["role"],
            parts=[types.Part.from_text(text=m["content"])]
        )
        for m in messages
    ]

    kwargs = dict(model=settings.GEMINI_TEXT_MODEL, contents=contents)
    if config:
        kwargs["config"] = config

    response = client.models.generate_content(**kwargs)

    usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        m = response.usage_metadata
        usage = {
            "prompt_tokens": getattr(m, "prompt_token_count", None),
            "output_tokens": getattr(m, "candidates_token_count", None),
            "total_tokens": getattr(m, "total_token_count", None),
        }

    return {"result": response.text, "model": settings.GEMINI_TEXT_MODEL, "usage": usage}


# ── Summarization ─────────────────────────────────────────────────────────────

STYLE_PROMPTS = {
    "concise": "Summarize the following text concisely in 2-4 sentences. Be precise and clear.",
    "detailed": "Provide a detailed summary of the following text, covering all key points and important details.",
    "bullet": "Summarize the following text as a clean bullet-point list of the key points. Start each bullet with '• '.",
}


def summarize(text: str, style: str = "concise") -> dict:
    system_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["concise"])
    return generate_text(
        prompt=f"Text to summarize:\n\n{text}",
        system_prompt=system_prompt
    )


# ── Image Understanding ───────────────────────────────────────────────────────

def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str
) -> dict:
    client = get_client()

    contents = [
        types.Part.from_text(text=prompt),
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
    ]

    response = client.models.generate_content(
        model=settings.GEMINI_VISION_MODEL,
        contents=contents,
    )

    usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        m = response.usage_metadata
        usage = {
            "prompt_tokens": getattr(m, "prompt_token_count", None),
            "output_tokens": getattr(m, "candidates_token_count", None),
            "total_tokens": getattr(m, "total_token_count", None),
        }

    return {"result": response.text, "model": settings.GEMINI_VISION_MODEL, "usage": usage}
