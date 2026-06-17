import os
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.domain.user_role import UserRole
from app.models.user import User
from app.services.audit import add_audit_event


class BootstrapAdminError(RuntimeError):
    pass


@dataclass(frozen=True)
class BootstrapAdminResult:
    action: str
    email: str
    user_id: str


def normalize_admin_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise BootstrapAdminError("ADMIN_EMAIL is required.")
    return normalized


def bootstrap_admin(db: Session, email: str, password: str | None = None) -> BootstrapAdminResult:
    normalized_email = normalize_admin_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is not None:
        if user.role != UserRole.ADMIN.value:
            user.role = UserRole.ADMIN.value
            user.is_active = True
            add_audit_event(
                db,
                actor=user,
                target_user_id=user.id,
                action="USER_PROMOTED_ADMIN",
                message="User promoted to ADMIN by bootstrap CLI.",
            )
            db.commit()
            db.refresh(user)
            return BootstrapAdminResult("promoted", user.email, user.id)
        return BootstrapAdminResult("already_admin", user.email, user.id)

    if password is None or not password:
        raise BootstrapAdminError("ADMIN_PASSWORD is required when creating a new admin user.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=UserRole.ADMIN.value,
        bridge_limit=1,
        is_active=True,
    )
    db.add(user)
    db.flush()
    add_audit_event(
        db,
        actor=user,
        target_user_id=user.id,
        action="USER_PROMOTED_ADMIN",
        message="Admin user created by bootstrap CLI.",
    )
    db.commit()
    db.refresh(user)
    return BootstrapAdminResult("created", user.email, user.id)


def main() -> int:
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL is required.", file=sys.stderr)
        return 1

    admin_email = os.getenv("ADMIN_EMAIL", "")
    admin_password = os.getenv("ADMIN_PASSWORD")

    try:
        with SessionLocal() as db:
            result = bootstrap_admin(db, admin_email, admin_password)
    except BootstrapAdminError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Admin bootstrap {result.action}: email={result.email} user_id={result.user_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
