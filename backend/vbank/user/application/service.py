from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from vbank.shared.errors import VBankError
from vbank.user.infrastructure.models import UserAccount

VALID_USER_ROLES = {"Client", "Operator", "Admin"}
VALID_USER_STATUSES = {"Active", "Blocked"}
USER_STATUS_TRANSITIONS = {("Active", "Blocked"), ("Blocked", "Active")}


@dataclass(frozen=True, slots=True)
class UserListQuery:
    role: str | None
    status: str | None
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class UserPage:
    users: list[UserAccount]
    limit: int
    offset: int
    total: int


@dataclass(frozen=True, slots=True)
class ChangeUserStatusCommand:
    user_id: UUID
    status: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class ChangeUserRoleCommand:
    user_id: UUID
    role: str


class UserRepository(Protocol):
    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[UserAccount]: ...

    def count_users(self, *, role: str | None, status: str | None) -> int: ...

    def find_user_by_id(self, user_id: UUID) -> UserAccount | None: ...

    def reason_code_allows_user_change(self, reason_code: str) -> bool: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def list_users(self, *, actor: UserAccount, query: UserListQuery) -> UserPage:
        self._ensure_actor_is_active(actor)
        self._ensure_role(actor, allowed_roles={"Operator", "Admin"})
        self._ensure_filter_is_valid(query)

        users = self.repository.list_users(
            role=query.role,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
        total = self.repository.count_users(role=query.role, status=query.status)
        return UserPage(users=users, limit=query.limit, offset=query.offset, total=total)

    def get_user(self, *, actor: UserAccount, user_id: UUID) -> UserAccount:
        self._ensure_actor_is_active(actor)
        self._ensure_role(actor, allowed_roles={"Operator", "Admin"})
        return self._get_visible_user(user_id)

    def change_status(
        self,
        *,
        actor: UserAccount,
        command: ChangeUserStatusCommand,
    ) -> UserAccount:
        self._ensure_actor_is_active(actor)
        self._ensure_role(actor, allowed_roles={"Operator"}, required_role="Operator")
        target_user = self._get_visible_user(command.user_id)

        if (target_user.status, command.status) not in USER_STATUS_TRANSITIONS:
            raise VBankError(
                code="USER_STATUS_TRANSITION_INVALID",
                message="Переход статуса пользователя недопустим",
                status_code=409,
                details={
                    "category": "object_state",
                    "current_status": target_user.status,
                    "requested_status": command.status,
                },
            )

        if not self.repository.reason_code_allows_user_change(command.reason_code):
            raise VBankError(
                code="REASON_CODE_NOT_ALLOWED",
                message="Причина решения не подходит для изменения пользователя",
                status_code=422,
                details={"category": "business_rule", "reason_code": command.reason_code},
            )

        target_user.status = command.status
        self._commit_or_raise()
        return target_user

    def change_role(
        self,
        *,
        actor: UserAccount,
        command: ChangeUserRoleCommand,
    ) -> UserAccount:
        self._ensure_actor_is_active(actor)
        self._ensure_role(actor, allowed_roles={"Admin"}, required_role="Admin")
        target_user = self._get_visible_user(command.user_id)
        target_user.role = command.role
        self._commit_or_raise()
        return target_user

    def _get_visible_user(self, user_id: UUID) -> UserAccount:
        user = self.repository.find_user_by_id(user_id)
        if user is None:
            raise VBankError(
                code="OBJECT_NOT_FOUND",
                message="Пользователь не найден",
                status_code=404,
                details={"category": "object_state"},
            )
        return user

    def _ensure_actor_is_active(self, actor: UserAccount) -> None:
        if actor.status == "Blocked":
            raise VBankError(
                code="USER_BLOCKED",
                message="Пользователь заблокирован",
                status_code=403,
                details={"category": "access"},
            )

    def _ensure_role(
        self,
        actor: UserAccount,
        *,
        allowed_roles: set[str],
        required_role: str | None = None,
    ) -> None:
        if actor.role in allowed_roles:
            return
        raise VBankError(
            code="ACCESS_DENIED",
            message="Доступ запрещён",
            status_code=403,
            details={
                "category": "access",
                "required_role": required_role or "/".join(sorted(allowed_roles)),
                "actor_role": actor.role,
            },
        )

    def _ensure_filter_is_valid(self, query: UserListQuery) -> None:
        if query.role is not None and query.role not in VALID_USER_ROLES:
            raise _filter_invalid("role")
        if query.status is not None and query.status not in VALID_USER_STATUSES:
            raise _filter_invalid("status")
        if query.limit < 1 or query.limit > 100:
            raise _filter_invalid("limit")
        if query.offset < 0:
            raise _filter_invalid("offset")

    def _commit_or_raise(self) -> None:
        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise


def _filter_invalid(field: str) -> VBankError:
    return VBankError(
        code="FILTER_INVALID",
        message="Параметры фильтрации недопустимы",
        status_code=400,
        details={"category": "validation", "field": field},
    )
