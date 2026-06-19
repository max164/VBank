from contextvars import ContextVar
from uuid import UUID

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def bind_request_id(request_id: str) -> object:
    return _request_id.set(request_id)


def reset_request_id(token: object) -> None:
    _request_id.reset(token)


def get_request_id() -> str:
    request_id = _request_id.get()
    if request_id is None:
        msg = "request_id is not bound to the current request"
        raise RuntimeError(msg)
    return request_id


def normalize_request_id(value: str | None, fallback: UUID) -> str:
    if not value:
        return str(fallback)

    try:
        return str(UUID(value))
    except ValueError:
        return str(fallback)
