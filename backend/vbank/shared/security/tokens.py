from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from vbank.shared.config import Settings
from vbank.shared.errors import VBankError


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    expires_at: datetime


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    status: str,
    settings: Settings,
    issued_at: datetime | None = None,
) -> tuple[str, datetime]:
    resolved_issued_at = issued_at or datetime.now(UTC)
    expires_at = resolved_issued_at + timedelta(minutes=settings.access_token_ttl_minutes)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "status": status,
            "type": "access",
            "iat": resolved_issued_at,
            "exp": expires_at,
        },
        settings.access_token_secret,
        algorithm=settings.access_token_algorithm,
    )
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.access_token_secret,
            algorithms=[settings.access_token_algorithm],
        )
    except InvalidTokenError as exc:
        raise VBankError(
            code="TOKEN_INVALID",
            message="Access token недействителен",
            status_code=401,
            details={"category": "access"},
        ) from exc

    if payload.get("type") != "access":
        raise VBankError(
            code="TOKEN_INVALID",
            message="Access token недействителен",
            status_code=401,
            details={"category": "access"},
        )

    try:
        user_id = UUID(str(payload["sub"]))
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise VBankError(
            code="TOKEN_INVALID",
            message="Access token недействителен",
            status_code=401,
            details={"category": "access"},
        ) from exc

    return AccessTokenClaims(user_id=user_id, expires_at=expires_at)


def create_refresh_token() -> str:
    return token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    return sha256(refresh_token.encode("utf-8")).hexdigest()
