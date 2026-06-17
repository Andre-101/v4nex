import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domain.user_role import UserRole
from app.models.user import User
from app.services.audit import add_audit_event


class UserCliError(RuntimeError):
    pass


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise UserCliError("email is required.")
    return normalized


def find_user_by_email(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        raise UserCliError(f"user not found: {email}")
    return user


def promote_admin(db: Session, email: str) -> str:
    user = find_user_by_email(db, email)
    user.role = UserRole.ADMIN.value
    user.is_active = True
    add_audit_event(
        db,
        actor=user,
        target_user_id=user.id,
        action="USER_PROMOTED_ADMIN",
        message="User promoted to ADMIN by CLI.",
    )
    db.commit()
    return f"User promoted to ADMIN: {user.email}"


def set_bridge_limit(db: Session, email: str, limit: int) -> str:
    if limit < 0:
        raise UserCliError("bridge limit must be zero or greater.")
    user = find_user_by_email(db, email)
    previous_limit = user.bridge_limit
    user.bridge_limit = limit
    add_audit_event(
        db,
        actor=user,
        target_user_id=user.id,
        action="USER_LIMIT_CHANGED",
        message="User bridge limit changed by CLI.",
        metadata={"previous_limit": previous_limit, "new_limit": limit},
    )
    db.commit()
    return f"Bridge limit updated: email={user.email} bridge_limit={user.bridge_limit}"


def set_active(db: Session, email: str, is_active: bool) -> str:
    user = find_user_by_email(db, email)
    previous_active = user.is_active
    user.is_active = is_active
    if previous_active != is_active:
        add_audit_event(
            db,
            actor=user,
            target_user_id=user.id,
            action="USER_UNSUSPENDED" if is_active else "USER_SUSPENDED",
            message="User reactivated by CLI." if is_active else "User suspended by CLI.",
        )
    db.commit()
    action = "reactivated" if is_active else "suspended"
    return f"User {action}: {user.email}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="v4nex user administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    promote = subparsers.add_parser("promote-admin", help="Promote an existing user to ADMIN")
    promote.add_argument("--email", required=True)

    limit = subparsers.add_parser("set-bridge-limit", help="Set bridge limit for a user")
    limit.add_argument("--email", required=True)
    limit.add_argument("--limit", required=True, type=int)

    suspend = subparsers.add_parser("suspend", help="Suspend a user")
    suspend.add_argument("--email", required=True)

    unsuspend = subparsers.add_parser("unsuspend", help="Reactivate a suspended user")
    unsuspend.add_argument("--email", required=True)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        with SessionLocal() as db:
            if args.command == "promote-admin":
                message = promote_admin(db, args.email)
            elif args.command == "set-bridge-limit":
                message = set_bridge_limit(db, args.email, args.limit)
            elif args.command == "suspend":
                message = set_active(db, args.email, False)
            elif args.command == "unsuspend":
                message = set_active(db, args.email, True)
            else:
                raise UserCliError(f"unsupported command: {args.command}")
    except UserCliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
