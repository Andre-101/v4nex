from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import ErrorCode


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
