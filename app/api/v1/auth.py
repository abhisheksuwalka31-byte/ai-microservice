from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.users import create_user, authenticate_user
from app.core.security import create_access_token
from app.schemas import UserRegisterRequest, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest):
    """
    Register a new user account and receive a JWT access token.
    """
    user = create_user(
        username=payload.username,
        email=str(payload.email),
        password=payload.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken."
        )
    token = create_access_token(subject=user["id"])
    return Token(
        access_token=token,
        user=UserResponse(**{k: user[k] for k in ["id", "username", "email", "created_at"]})
    )


@router.post("/token")
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint — used by Swagger UI's Authorize button.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(subject=user["id"]), "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login_json(payload: dict):
    """
    JSON login endpoint. Send `{"username": "...", "password": "..."}`.
    """
    user = authenticate_user(payload.get("username", ""), payload.get("password", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )
    token = create_access_token(subject=user["id"])
    return Token(
        access_token=token,
        user=UserResponse(**{k: user[k] for k in ["id", "username", "email", "created_at"]})
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user)):
    """
    Return the currently authenticated user's profile.
    """
    return UserResponse(**{k: current_user[k] for k in ["id", "username", "email", "created_at"]})
