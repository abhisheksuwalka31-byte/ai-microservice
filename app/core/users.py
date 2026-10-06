from typing import Optional, List
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models.user import User, UserRole
from app.core.security import get_password_hash, verify_password


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: str = UserRole.DEVELOPER.value
) -> Optional[User]:
    """Create a new user with hashed password and role."""
    # Check if username or email already exists
    existing = db.execute(
        select(User).where((User.username == username) | (User.email == email))
    ).scalar_one_or_none()

    if existing:
        return None

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Query user by username."""
    return db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int, include_relations: bool = False) -> Optional[User]:
    """Query user by primary key. Uses selectinload to prevent N+1 queries when relations are needed."""
    stmt = select(User).where(User.id == user_id)
    if include_relations:
        stmt = stmt.options(selectinload(User.audit_logs), selectinload(User.inference_logs))
    return db.execute(stmt).scalar_one_or_none()


def get_users_list(db: Session, skip: int = 0, limit: int = 50) -> List[User]:
    """Get list of users with eager-loaded relationships to completely prevent N+1 queries."""
    stmt = (
        select(User)
        .options(selectinload(User.audit_logs), selectinload(User.inference_logs))
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Verify username and password credentials."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
