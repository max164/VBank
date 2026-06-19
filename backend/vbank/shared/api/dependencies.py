from uuid import UUID

from fastapi import Request

from vbank.shared.config import Settings
from vbank.shared.errors import VBankError

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


def get_request_id(request: Request) -> str:
    return str(request.state.request_id)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_idempotency_key(request: Request) -> UUID:
    raw_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
    if raw_key is None:
        raise VBankError(
            code="IDEMPOTENCY_KEY_REQUIRED",
            message="Изменяющий запрос требует Idempotency-Key",
            status_code=400,
            details={"category": "validation"},
        )

    try:
        return UUID(raw_key)
    except ValueError as exc:
        raise VBankError(
            code="IDEMPOTENCY_KEY_INVALID",
            message="Idempotency-Key должен быть UUID",
            status_code=400,
            details={"category": "validation"},
        ) from exc
