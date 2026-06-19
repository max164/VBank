from typing import Any
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from vbank.shared.api.context import get_request_id
from vbank.shared.api.responses import error_response
from vbank.shared.errors import VBankError

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(VBankError, handle_vbank_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_vbank_error(request: Request, exc: VBankError) -> JSONResponse:
    return _json_error(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    field_errors = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        field_errors.append(
            {
                "field": location,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return _json_error(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Запрос содержит недопустимые поля",
        details={
            "category": "validation",
            "field_errors": field_errors,
        },
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    code, message, category = _http_error_contract(exc.status_code)
    return _json_error(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details={"category": category},
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("api_unhandled_error", error_type=type(exc).__name__)
    return _json_error(
        request=request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="Внутренняя ошибка сервера",
        details={"category": "internal"},
    )


def _json_error(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any],
) -> JSONResponse:
    request_id = _safe_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=error_response(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


def _safe_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is not None:
        return str(request_id)

    try:
        return get_request_id()
    except RuntimeError:
        return str(uuid4())


def _http_error_contract(status_code: int) -> tuple[str, str, str]:
    if status_code == 401:
        return "AUTHENTICATION_REQUIRED", "Требуется аутентификация", "access"
    if status_code == 403:
        return "ACCESS_DENIED", "Доступ запрещён", "access"
    if status_code == 404:
        return "OBJECT_NOT_FOUND", "Объект не найден", "object_state"
    if status_code == 405:
        return "VALIDATION_ERROR", "Метод не поддерживается", "validation"
    if 400 <= status_code < 500:
        return "VALIDATION_ERROR", "Запрос не может быть обработан", "validation"
    return "INTERNAL_ERROR", "Внутренняя ошибка сервера", "internal"
