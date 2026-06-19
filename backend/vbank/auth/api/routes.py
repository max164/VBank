from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from vbank.auth.api.dependencies import get_auth_service, require_access_token
from vbank.auth.api.schemas import LoginRequest, RefreshTokenRequest, RegisterRequest
from vbank.auth.application.service import (
    AuthService,
    LoginCommand,
    RegisterUserCommand,
)
from vbank.auth.infrastructure.models import RefreshSession
from vbank.request.infrastructure.models import Request as Application
from vbank.shared.api.dependencies import (
    get_request_id,
    get_settings,
    require_idempotency_key,
)
from vbank.shared.api.responses import success_response
from vbank.shared.config import Settings
from vbank.shared.errors import VBankError
from vbank.user.infrastructure.models import UserAccount

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register")
def register(
    body: RegisterRequest,
    request_id: Annotated[str, Depends(get_request_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
) -> dict[str, Any]:
    result = auth_service.register_user(
        RegisterUserCommand(
            email=body.email,
            username=body.username,
            phone_number=body.phone_number,
            password=body.password,
        )
    )
    return success_response(
        {
            "result_type": result.result_type,
            "user": _serialize_user(result.user) if result.user is not None else None,
            "application": (
                _serialize_application(result.application)
                if result.application is not None
                else None
            ),
        },
        request_id=request_id,
    )


@auth_router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    request_id: Annotated[str, Depends(get_request_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
) -> dict[str, Any]:
    result = auth_service.login(
        LoginCommand(
            login=body.login,
            password=body.password,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
    )
    return success_response(
        _serialize_token_result(
            access_token=result.access_token,
            access_token_expires_at=result.access_token_expires_at,
            refresh_token=result.refresh_token,
            refresh_session=result.refresh_session,
            user=result.user,
            response=response,
            settings=settings,
        ),
        request_id=request_id,
    )


@auth_router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    request_id: Annotated[str, Depends(get_request_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    body: RefreshTokenRequest | None = None,
) -> dict[str, Any]:
    result = auth_service.refresh(_extract_refresh_token(body, request, settings))
    return success_response(
        _serialize_token_result(
            access_token=result.access_token,
            access_token_expires_at=result.access_token_expires_at,
            refresh_token=result.refresh_token,
            refresh_session=result.refresh_session,
            user=result.user,
            response=response,
            settings=settings,
        ),
        request_id=request_id,
    )


@auth_router.post("/logout")
def logout(
    request: Request,
    response: Response,
    request_id: Annotated[str, Depends(get_request_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    body: RefreshTokenRequest | None = None,
) -> dict[str, Any]:
    result = auth_service.logout(_extract_refresh_token(body, request, settings))
    if settings.refresh_token_transport == "cookie":
        response.delete_cookie(settings.refresh_token_cookie_name)
    return success_response(
        {
            "success": result.success,
            "refresh_session_id": str(result.refresh_session_id),
            "revoked_at": _serialize_datetime(result.revoked_at),
        },
        request_id=request_id,
    )


@auth_router.get("/me")
def me(
    request_id: Annotated[str, Depends(get_request_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str, Depends(require_access_token)],
) -> dict[str, Any]:
    user = auth_service.get_current_user(access_token)
    return success_response(_serialize_user(user), request_id=request_id)


def _extract_refresh_token(
    body: RefreshTokenRequest | None,
    request: Request,
    settings: Settings,
) -> str:
    refresh_token = body.refresh_token if body is not None else None
    if refresh_token is None:
        refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    if refresh_token is None:
        raise VBankError(
            code="REFRESH_SESSION_INVALID",
            message="Refresh-сессия недействительна",
            status_code=401,
            details={"category": "access"},
        )
    return refresh_token


def _serialize_token_result(
    *,
    access_token: str,
    access_token_expires_at: datetime,
    refresh_token: str,
    refresh_session: RefreshSession,
    user: UserAccount,
    response: Response,
    settings: Settings,
) -> dict[str, Any]:
    body_refresh_token = refresh_token
    if settings.refresh_token_transport == "cookie":
        _set_refresh_cookie(response, settings, refresh_token, refresh_session.expires_at)
        body_refresh_token = None

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "access_token_expires_at": _serialize_datetime(access_token_expires_at),
        "refresh_token": body_refresh_token,
        "refresh_session": _serialize_refresh_session(refresh_session),
        "user": _serialize_user(user),
    }


def _set_refresh_cookie(
    response: Response,
    settings: Settings,
    refresh_token: str,
    expires_at: datetime,
) -> None:
    max_age = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.refresh_token_cookie_secure,
        samesite=settings.refresh_token_cookie_samesite,
    )


def _serialize_user(user: UserAccount) -> dict[str, Any]:
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "username": user.username,
        "phone_number": user.phone_number,
        "role": user.role,
        "status": user.status,
        "registered_at": _serialize_datetime(user.registered_at),
    }


def _serialize_refresh_session(refresh_session: RefreshSession) -> dict[str, Any]:
    return {
        "refresh_session_id": str(refresh_session.refresh_session_id),
        "issued_at": _serialize_datetime(refresh_session.issued_at),
        "expires_at": _serialize_datetime(refresh_session.expires_at),
        "revoked_at": _serialize_optional_datetime(refresh_session.revoked_at),
    }


def _serialize_application(application: Application) -> dict[str, Any]:
    payload = dict(application.payload)
    payload.pop("password_hash", None)
    return {
        "application_id": str(application.request_id),
        "request_type": application.request_type,
        "status": application.status,
        "initiator_user_id": str(application.initiator_user_id),
        "operator_user_id": (
            str(application.operator_user_id)
            if application.operator_user_id is not None
            else None
        ),
        "payload": payload,
        "reason_code": application.reason_code,
        "result": _serialize_application_result(application),
        "created_at": _serialize_datetime(application.created_at),
        "decided_at": _serialize_optional_datetime(application.decided_at),
    }


def _serialize_application_result(application: Application) -> dict[str, str] | None:
    if application.result_entity_type is None or application.result_entity_id is None:
        return None
    return {
        "entity_type": application.result_entity_type,
        "entity_id": str(application.result_entity_id),
    }


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _serialize_datetime(value)


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
