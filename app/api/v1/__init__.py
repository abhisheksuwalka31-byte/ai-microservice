from fastapi import APIRouter
from app.api.v1 import auth, ai

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Inference"])
