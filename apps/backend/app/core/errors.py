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


ERROR_STATUS_CODES: dict[ErrorCode, int] = {
    ErrorCode.INVALID_EMAIL: 422,
    ErrorCode.EMAIL_ALREADY_EXISTS: 409,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.INVALID_SUBDOMAIN: 422,
    ErrorCode.RESERVED_SUBDOMAIN: 422,
    ErrorCode.SUBDOMAIN_ALREADY_EXISTS: 409,
    ErrorCode.INVALID_IPV6: 422,
    ErrorCode.INVALID_PORT: 422,
    ErrorCode.BRIDGE_NOT_FOUND: 404,
    ErrorCode.INVALID_STATE_TRANSITION: 409,
    ErrorCode.TCP_VALIDATION_FAILED: 422,
    ErrorCode.CADDY_ACTIVATION_FAILED: 409,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INTERNAL_ERROR: 500,
}


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code or ERROR_STATUS_CODES.get(code, 400)
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
