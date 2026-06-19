from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from vbank.auth.api.dependencies import get_current_user
from vbank.shared.api.dependencies import get_request_id, require_idempotency_key
from vbank.shared.api.responses import page_response, success_response
from vbank.user.api.dependencies import get_user_service
from vbank.user.api.schemas import ChangeUserRoleRequest, ChangeUserStatusRequest
from vbank.user.application.service import (
    ChangeUserRoleCommand,
    ChangeUserStatusCommand,
    UserListQuery,
    UserService,
)
from vbank.user.infrastructure.models import UserAccount

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
def list_users(
    request_id: Annotated[str, Depends(get_request_id)],
    actor: Annotated[UserAccount, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    role: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    page = user_service.list_users(
        actor=actor,
        query=UserListQuery(role=role, status=status, limit=limit, offset=offset),
    )
    return page_response(
        [_serialize_user(user) for user in page.users],
        request_id=request_id,
        limit=page.limit,
        offset=page.offset,
        total=page.total,
    )


@users_router.get("/{user_id}")
def get_user(
    user_id: UUID,
    request_id: Annotated[str, Depends(get_request_id)],
    actor: Annotated[UserAccount, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, Any]:
    user = user_service.get_user(actor=actor, user_id=user_id)
    return success_response(_serialize_user(user), request_id=request_id)


@users_router.patch("/{user_id}/status")
def change_user_status(
    user_id: UUID,
    body: ChangeUserStatusRequest,
    request_id: Annotated[str, Depends(get_request_id)],
    actor: Annotated[UserAccount, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
) -> dict[str, Any]:
    user = user_service.change_status(
        actor=actor,
        command=ChangeUserStatusCommand(
            user_id=user_id,
            status=body.status,
            reason_code=body.reason_code,
        ),
    )
    return success_response(_serialize_user(user), request_id=request_id)


@users_router.patch("/{user_id}/role")
def change_user_role(
    user_id: UUID,
    body: ChangeUserRoleRequest,
    request_id: Annotated[str, Depends(get_request_id)],
    actor: Annotated[UserAccount, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    _idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
) -> dict[str, Any]:
    user = user_service.change_role(
        actor=actor,
        command=ChangeUserRoleCommand(user_id=user_id, role=body.role),
    )
    return success_response(_serialize_user(user), request_id=request_id)


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


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
