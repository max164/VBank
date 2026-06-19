from time import perf_counter
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from vbank.shared.api.context import (
    REQUEST_ID_HEADER,
    bind_request_id,
    normalize_request_id,
    reset_request_id,
)

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = normalize_request_id(
            request.headers.get(REQUEST_ID_HEADER),
            fallback=uuid4(),
        )
        request.state.request_id = request_id

        token = bind_request_id(request_id)
        bind_contextvars(request_id=request_id)
        started_at = perf_counter()

        logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info(
                "http_request_finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        finally:
            reset_request_id(token)
            clear_contextvars()
