from sqlalchemy import select

from app.cli.bootstrap_admin import BootstrapAdminError, bootstrap_admin
from app.core.security import verify_password
from app.db.session import SessionLocal
from app.domain.user_role import UserRole
from app.models.user import User


def test_bootstrap_creates_admin_if_missing() -> None:
    with SessionLocal() as db:
        result = bootstrap_admin(db, "Admin@Example.com", "strong-password")

    assert result.action == "created"
    assert result.email == "admin@example.com"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert user is not None
        assert user.role == UserRole.ADMIN.value
        assert user.password_hash != "strong-password"
        assert verify_password("strong-password", user.password_hash)


def test_bootstrap_promotes_existing_user() -> None:
    with SessionLocal() as db:
        user = User(
            email="user@example.com",
            password_hash="existing-hash",
            role=UserRole.USER.value,
        )
        db.add(user)
        db.commit()

    with SessionLocal() as db:
        result = bootstrap_admin(db, "user@example.com")

    assert result.action == "promoted"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert user.role == UserRole.ADMIN.value
        assert user.password_hash == "existing-hash"


def test_bootstrap_requires_password_for_new_admin() -> None:
    with SessionLocal() as db:
        try:
            bootstrap_admin(db, "new@example.com")
        except BootstrapAdminError as exc:
            assert "ADMIN_PASSWORD" in str(exc)
        else:
            raise AssertionError("Expected BootstrapAdminError")


def test_bootstrap_does_not_print_password(capsys) -> None:
    with SessionLocal() as db:
        result = bootstrap_admin(db, "quiet@example.com", "super-secret-password")

    print(f"Admin bootstrap {result.action}: email={result.email} user_id={result.user_id}")
    captured = capsys.readouterr()

    assert "super-secret-password" not in captured.out
    assert "super-secret-password" not in captured.err
