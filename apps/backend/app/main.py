from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.auth import router as auth_router
from app.api.routes.bridges import router as bridges_router
from app.api.routes.health import router as health_router
from app.core.errors import AppError, ErrorCode, error_response
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="v4nex-backend", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(bridges_router)


@app.exception_handler(AppError)
def app_error_handler(_request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
def validation_error_handler(_request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_response(
            ErrorCode.INTERNAL_ERROR,
            "Request validation failed.",
            {"errors": exc.errors()},
        ),
    )


@app.exception_handler(StarletteHTTPException)
def http_error_handler(_request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 401:
        code = ErrorCode.UNAUTHORIZED
        message = "Unauthorized."
    elif exc.status_code == 404:
        code = ErrorCode.BRIDGE_NOT_FOUND
        message = "Resource was not found."
    else:
        code = ErrorCode.INTERNAL_ERROR
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, message),
    )
