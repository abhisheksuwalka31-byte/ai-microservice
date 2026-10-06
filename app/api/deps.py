from typing import List, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.users import get_user_by_id
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate bearer token and retrieve user from database."""
    user_id_str = decode_access_token(token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Corrupted token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive."
        )
    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that current user belongs to one of the specified roles.
    """
    allowed_values = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_values)}; your role: '{current_user.role}'"
            )
        return current_user

    return role_checker


def record_audit(
    db: Session,
    user_id: int,
    action: str,
    resource: str,
    ip_address: str = "127.0.0.1",
    status_code: int = 200
) -> AuditLog:
    """Record an audit trail entry for sensitive actions."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        ip_address=ip_address,
        status_code=status_code
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
