from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_EMAIL = "INVALID_EMAIL"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_SUBDOMAIN = "INVALID_SUBDOMAIN"
    RESERVED_SUBDOMAIN = "RESERVED_SUBDOMAIN"
    SUBDOMAIN_ALREADY_EXISTS = "SUBDOMAIN_ALREADY_EXISTS"
    INVALID_IPV6 = "INVALID_IPV6"
    INVALID_PORT = "INVALID_PORT"
    BRIDGE_NOT_FOUND = "BRIDGE_NOT_FOUND"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    TCP_VALIDATION_FAILED = "TCP_VALIDATION_FAILED"
    CADDY_ACTIVATION_FAILED = "CADDY_ACTIVATION_FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def error_response(
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "error": {
            "code": code.value,
            "message": message,
            "details": details or {},
        }
    }
