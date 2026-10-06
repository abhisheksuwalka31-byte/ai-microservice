from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.users import create_user, authenticate_user, get_users_list
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.schemas import UserRegisterRequest, UserResponse, UserDetailResponse, AuditLogResponse, Token
from app.api.deps import get_current_user, require_role, record_audit

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account with role selection (admin, developer, viewer).
    Issues JWT access token and records audit event.
    """
    role_val = payload.role.value if payload.role else UserRole.DEVELOPER.value
    user = create_user(
        db=db,
        username=payload.username,
        email=str(payload.email),
        password=payload.password,
        role=role_val
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already taken."
        )

    # Record audit event
    record_audit(
        db=db,
        user_id=user.id,
        action="user.register",
        resource="/api/v1/auth/register",
        ip_address=request.client.host if request.client else "127.0.0.1",
        status_code=status.HTTP_201_CREATED
    )

    token = create_access_token(subject=user.id)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/token")
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint — used by Swagger UI's Authorize button.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    record_audit(
        db=db,
        user_id=user.id,
        action="user.login_oauth",
        resource="/api/v1/auth/token",
        ip_address=request.client.host if request.client else "127.0.0.1",
        status_code=200
    )

    return {"access_token": create_access_token(subject=user.id), "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login_json(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    JSON login endpoint. Send `{"username": "...", "password": "..."}`.
    """
    user = authenticate_user(db, payload.get("username", ""), payload.get("password", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    record_audit(
        db=db,
        user_id=user.id,
        action="user.login_json",
        resource="/api/v1/auth/login",
        ip_address=request.client.host if request.client else "127.0.0.1",
        status_code=200
    )

    token = create_access_token(subject=user.id)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile with role and timestamp.
    """
    return UserResponse.model_validate(current_user)


# ── RBAC Protected Endpoints ──────────────────────────────────────────────────

@router.get("/users", response_model=List[UserDetailResponse], summary="List Users (Admin Only)")
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    **Admin Only (RBAC)**: Retrieve all registered users with relationships.
    Uses eager loading (`selectinload`) to completely prevent N+1 query patterns.
    """
    users = get_users_list(db, skip=skip, limit=limit)
    return [UserDetailResponse.model_validate(u) for u in users]


@router.get("/audit-logs", response_model=List[AuditLogResponse], summary="View Audit Trail (Admin Only)")
def get_audit_trail(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    **Admin Only (RBAC)**: View system-wide security and access audit logs.
    """
    stmt = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = db.execute(stmt).scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]
