"""
Database seed script to create demo users with various RBAC roles:
- admin (Role: admin)
- alex_dev (Role: developer)
- sam_viewer (Role: viewer)
"""
from app.core.database import SessionLocal, Base, engine
from app.core.users import create_user, get_user_by_username
from app.models.user import UserRole


def seed_demo_users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo_accounts = [
            ("admin", "admin@platform.local", "password123", UserRole.ADMIN.value),
            ("alex_dev", "alex@platform.local", "password123", UserRole.DEVELOPER.value),
            ("sam_viewer", "sam@platform.local", "password123", UserRole.VIEWER.value),
        ]

        for username, email, password, role in demo_accounts:
            existing = get_user_by_username(db, username)
            if not existing:
                create_user(db, username=username, email=email, password=password, role=role)
                print(f"✅ Created demo user '{username}' with role '{role}'")
            else:
                print(f"ℹ️ User '{username}' already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_users()
