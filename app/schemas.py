from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


# ── Auth & User Schemas ───────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Optional[UserRole] = Field(default=UserRole.DEVELOPER, description="User role: admin, developer, or viewer")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Audit & Observability Schemas ─────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    resource: str
    ip_address: Optional[str]
    status_code: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InferenceLogResponse(BaseModel):
    id: int
    user_id: int
    endpoint: str
    model_name: str
    prompt_tokens: Optional[int]
    output_tokens: Optional[int]
    latency_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    audit_logs: List[AuditLogResponse] = []
    inference_logs: List[InferenceLogResponse] = []


# ── AI Inference Schemas ──────────────────────────────────────────────────────

class TextRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000, description="Text prompt for the model")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="Optional system instruction")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature (0.0–2.0)")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Maximum tokens in response")


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|model)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, description="Conversation history")
    system_prompt: Optional[str] = Field(None, max_length=2000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=20000, description="Text to summarize")
    style: str = Field("concise", pattern=r"^(concise|detailed|bullet)$", description="Summary style: concise | detailed | bullet")


class AIResponse(BaseModel):
    result: str
    model: str
    usage: Optional[dict] = None
