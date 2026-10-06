"""
Gemini AI service layer.
Uses google-genai SDK when GEMINI_API_KEY is configured.
Provides intelligent local simulation fallback when GEMINI_API_KEY is not set,
allowing full UI evaluation and demo recording out-of-the-box.
"""
import base64
import time
from typing import Optional
from app.core.config import settings


def is_live_configured() -> bool:
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")


# Lazy singleton client
_client = None


def get_client():
    global _client
    if _client is None and is_live_configured():
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


# ── Text Generation ───────────────────────────────────────────────────────────

def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    if is_live_configured():
        from google.genai import types
        client = get_client()

        kwargs_cfg = {}
        if system_prompt:
            kwargs_cfg["system_instruction"] = system_prompt
        if temperature is not None:
            kwargs_cfg["temperature"] = temperature
        if max_tokens is not None:
            kwargs_cfg["max_output_tokens"] = max_tokens
        config = types.GenerateContentConfig(**kwargs_cfg) if kwargs_cfg else None

        kwargs = dict(model=settings.GEMINI_TEXT_MODEL, contents=prompt)
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

    # Simulation Fallback (When API Key is not set)
    p_lower = prompt.lower()
    if "python" in p_lower or "code" in p_lower or "function" in p_lower or "fibonacci" in p_lower:
        result_text = (
            "Here is the requested implementation:\n\n"
            "```python\n"
            "def fibonacci(n: int) -> int:\n"
            "    \"\"\"Compute the n-th Fibonacci number using memoization.\"\"\"\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    elif n == 1:\n"
            "        return 1\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b\n\n"
            "# Example usage:\n"
            "if __name__ == '__main__':\n"
            "    print([fibonacci(i) for i in range(10)])\n"
            "```\n\n"
            "This solution runs in O(n) time and O(1) auxiliary space."
        )
    else:
        result_text = (
            f"Based on your query: \"{prompt}\"\n\n"
            "Artificial intelligence microservices offer a scalable, decoupled architecture for running machine learning workloads. "
            "Key architectural advantages include:\n"
            "1. **Independent Scalability**: Inference nodes can autoscale based on compute pressure.\n"
            "2. **Strict Schema Contracts**: Pydantic v2 ensures type-safe requests and responses.\n"
            "3. **Zero Trust Security**: Role-based access control and JWT bearer authorization prevent unauthorized model execution."
        )

    return {
        "result": result_text,
        "model": f"{settings.GEMINI_TEXT_MODEL} (local-engine)",
        "usage": {"prompt_tokens": len(prompt.split()) * 2, "output_tokens": 128, "total_tokens": len(prompt.split()) * 2 + 128}
    }


# ── Multi-turn Chat ───────────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> dict:
    if is_live_configured():
        from google.genai import types
        client = get_client()

        kwargs_cfg = {}
        if system_prompt:
            kwargs_cfg["system_instruction"] = system_prompt
        if temperature is not None:
            kwargs_cfg["temperature"] = temperature
        if max_tokens is not None:
            kwargs_cfg["max_output_tokens"] = max_tokens
        config = types.GenerateContentConfig(**kwargs_cfg) if kwargs_cfg else None

        contents = [
            types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])])
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

    # Simulation Fallback for Chat
    last_user_msg = messages[-1]["content"] if messages else ""
    user_q = last_user_msg.lower()

    if "hello" in user_q or "hi" in user_q or "hey" in user_q:
        reply = "Hello! I am your AI Microservice assistant. I'm connected and ready to assist you with coding, architecture, text generation, or analysis. What would you like to work on?"
    elif "who are you" in user_q or "what are you" in user_q:
        reply = "I am a containerized AI Microservice gateway running on FastAPI. I provide role-based access control, persistent audit logging, and inference endpoints for text and multimodal tasks."
    elif "name" in user_q and any(m["role"] == "user" and "my name is" in m["content"].lower() for m in messages):
        # Context extraction from conversation history
        user_name = "there"
        for m in messages:
            if "my name is " in m["content"].lower():
                parts = m["content"].lower().split("my name is ")
                if len(parts) > 1:
                    user_name = parts[1].split()[0].title()
        reply = f"Your name is {user_name}! I remember from earlier in our conversation."
    elif "help" in user_q:
        reply = "I can assist you with:\n• Generating and reviewing code\n• Summarizing long documents\n• Analyzing diagrams and images\n• Answering technical and general questions."
    else:
        reply = (
            f"Regarding '{last_user_msg}':\n\n"
            "That's an insightful question. When building scalable microservices, combining modular endpoints with clear schema contracts "
            "allows frontends and downstream services to communicate seamlessly while maintaining strict authorization boundaries."
        )

    return {
        "result": reply,
        "model": f"{settings.GEMINI_TEXT_MODEL} (local-engine)",
        "usage": {"prompt_tokens": 42, "output_tokens": 85, "total_tokens": 127}
    }


# ── Summarization ─────────────────────────────────────────────────────────────

STYLE_PROMPTS = {
    "concise": "Summarize the following text concisely in 2-4 sentences.",
    "detailed": "Provide a detailed summary of the following text covering all key points.",
    "bullet": "Summarize the following text as a clean bullet-point list of the key points.",
}


def summarize(text: str, style: str = "concise") -> dict:
    if is_live_configured():
        system_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["concise"])
        return generate_text(prompt=f"Text to summarize:\n\n{text}", system_prompt=system_prompt)

    # Simulation Fallback for Summarization
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    if style == "bullet":
        bullets = [f"• {s[:100]}." for s in sentences[:4]]
        if not bullets:
            bullets = ["• Primary insight extracted from source material."]
        result = "\n".join(bullets)
    elif style == "detailed":
        preview = ". ".join(sentences[:3]) + "." if sentences else text[:200]
        result = f"Detailed Overview:\n\nThe provided document outlines several essential facets: {preview}\n\nKey takeaways emphasize architectural modularity, predictable throughput, and streamlined maintainability."
    else:  # concise
        preview = ". ".join(sentences[:2]) + "." if len(sentences) >= 2 else (sentences[0] + "." if sentences else text[:150])
        result = f"Summary: {preview}"

    return {
        "result": result,
        "model": f"{settings.GEMINI_TEXT_MODEL} (local-engine)",
        "usage": {"prompt_tokens": len(text.split()), "output_tokens": 64, "total_tokens": len(text.split()) + 64}
    }


# ── Image Understanding ───────────────────────────────────────────────────────

def analyze_image(image_bytes: bytes, mime_type: str, prompt: str) -> dict:
    if is_live_configured():
        from google.genai import types
        client = get_client()
        contents = [
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ]
        response = client.models.generate_content(model=settings.GEMINI_VISION_MODEL, contents=contents)
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            m = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(m, "prompt_token_count", None),
                "output_tokens": getattr(m, "candidates_token_count", None),
                "total_tokens": getattr(m, "total_token_count", None),
            }
        return {"result": response.text, "model": settings.GEMINI_VISION_MODEL, "usage": usage}

    # Simulation Fallback for Multimodal Vision
    size_kb = round(len(image_bytes) / 1024, 1)
    analysis = (
        f"Visual Analysis Report (MIME: {mime_type}, Size: {size_kb} KB):\n\n"
        f"Prompt: \"{prompt}\"\n\n"
        "1. **Content Detection**: High-clarity digital image containing structured visual components.\n"
        "2. **Extracted Features**: The image exhibits distinct foreground elements with sharp contrast suitable for OCR and object classification.\n"
        "3. **Synthesis**: The uploaded graphic aligns directly with technical documentation and UI workflows."
    )
    return {
        "result": analysis,
        "model": f"{settings.GEMINI_VISION_MODEL} (local-engine)",
        "usage": {"prompt_tokens": 120, "output_tokens": 95, "total_tokens": 215}
    }
