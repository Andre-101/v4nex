import re

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


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
    validate_password(payload.password)

    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise AppError(
            code=ErrorCode.EMAIL_ALREADY_EXISTS,
            message="Email already exists.",
        )

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Invalid credentials.",
        )

    return TokenResponse(access_token=create_access_token(user.id))
