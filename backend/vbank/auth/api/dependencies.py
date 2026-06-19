from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from vbank.auth.application.service import AuthService
from vbank.auth.infrastructure.repositories import SqlAlchemyAuthRepository
from vbank.shared.api.dependencies import get_session, get_settings
from vbank.shared.config import Settings
from vbank.shared.errors import VBankError


def get_auth_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(session), settings)


def require_access_token(request: Request) -> str:
    raw_authorization = request.headers.get("Authorization")
    if raw_authorization is None:
        raise VBankError(
            code="AUTHENTICATION_REQUIRED",
            message="Требуется Authorization: Bearer",
            status_code=401,
            details={"category": "access"},
        )

    scheme, separator, token = raw_authorization.partition(" ")
    if separator == "" or scheme.lower() != "bearer" or token == "":
        raise VBankError(
            code="TOKEN_INVALID",
            message="Access token недействителен",
            status_code=401,
            details={"category": "access"},
        )
    return token
