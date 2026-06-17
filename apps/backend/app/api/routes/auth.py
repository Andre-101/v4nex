import re

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import check_rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.domain.user_role import UserRole
from app.models.user import User
from app.models.bridge import Bridge
from app.schemas.auth import CurrentUserResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.audit import add_audit_event


router = APIRouter(prefix="/_v4nex/auth", tags=["auth"])
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise AppError(
            code=ErrorCode.INVALID_EMAIL,
            message="Email must be valid.",
            details={"email": email},
        )
    return normalized


def validate_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Password must be at least 8 characters.",
        )
    return password


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    email = validate_email(payload.email)
    check_rate_limit("auth.register", email)
    validate_password(payload.password)

    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise AppError(
            code=ErrorCode.EMAIL_ALREADY_EXISTS,
            message="Email already exists.",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER.value,
        bridge_limit=1,
        is_active=True,
    )
    db.add(user)
    db.flush()
    add_audit_event(
        db,
        actor=user,
        target_user_id=user.id,
        action="USER_REGISTERED",
        message="User registered.",
    )
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        bridge_limit=user.bridge_limit,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    check_rate_limit("auth.login", email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Invalid credentials.",
        )
    if not user.is_active:
        raise AppError(
            code=ErrorCode.USER_INACTIVE,
            message="User account is suspended.",
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=CurrentUserResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    bridges_used = db.scalar(
        select(func.count()).select_from(Bridge).where(Bridge.user_id == current_user.id)
    )
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        bridge_limit=current_user.bridge_limit,
        is_active=current_user.is_active,
        bridges_used=bridges_used or 0,
    )
