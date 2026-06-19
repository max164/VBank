from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from vbank.auth.infrastructure.models import RefreshSession
from vbank.request.infrastructure.models import Request
from vbank.shared.config import Settings
from vbank.shared.errors import VBankError
from vbank.shared.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from vbank.user.infrastructure.models import UserAccount


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    username: str
    phone_number: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginCommand:
    login: str
    password: str
    user_agent: str | None
    ip_address: str | None


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    result_type: str
    user: UserAccount | None
    application: Request | None


@dataclass(frozen=True, slots=True)
class TokenIssueResult:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_session: RefreshSession
    user: UserAccount


@dataclass(frozen=True, slots=True)
class TokenRefreshResult:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_session: RefreshSession
    user: UserAccount


@dataclass(frozen=True, slots=True)
class LogoutResult:
    success: bool
    refresh_session_id: UUID
    revoked_at: datetime


class AuthRepository(Protocol):
    def get_system_setting(self, key: str) -> str | None: ...

    def identity_exists(self, *, email: str, username: str, phone_number: str) -> bool: ...

    def pending_registration_identity_exists(
        self,
        *,
        email: str,
        username: str,
        phone_number: str,
    ) -> bool: ...

    def find_user_by_login(self, login: str) -> UserAccount | None: ...

    def find_user_by_id(self, user_id: UUID) -> UserAccount | None: ...

    def has_pending_registration_for_user(self, user_id: UUID) -> bool: ...

    def has_pending_registration_for_login(self, login: str) -> bool: ...

    def find_refresh_session_by_token_hash(self, token_hash: str) -> RefreshSession | None: ...

    def add_user(self, user: UserAccount) -> None: ...

    def add_application(self, application: Request) -> None: ...

    def add_refresh_session(self, refresh_session: RefreshSession) -> None: ...

    def flush(self) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def register_user(self, command: RegisterUserCommand) -> RegistrationResult:
        self._ensure_identity_is_available(command)
        registration_mode = self.repository.get_system_setting("registration_mode") or "auto"
        if registration_mode not in {"auto", "manual"}:
            raise VBankError(
                code="SETTING_VALUE_INVALID",
                message="Режим регистрации недопустим",
                status_code=422,
                details={"category": "validation", "key": "registration_mode"},
            )

        now = _utc_now()
        user = UserAccount(
            user_id=uuid4(),
            email=command.email,
            username=command.username,
            phone_number=command.phone_number,
            password_hash=hash_password(command.password),
            role="Client",
            status="Active",
            registered_at=now,
        )

        try:
            self.repository.add_user(user)
            self.repository.flush()

            if registration_mode == "manual":
                application = Request(
                    request_id=uuid4(),
                    request_type="UserRegistration",
                    status="PendingApproval",
                    initiator_user_id=user.user_id,
                    operator_user_id=None,
                    payload={
                        "email": user.email,
                        "username": user.username,
                        "phone_number": user.phone_number,
                        "password_hash": user.password_hash,
                    },
                    reason_code=None,
                    result_entity_type=None,
                    result_entity_id=None,
                    created_at=now,
                    decided_at=None,
                )
                self.repository.add_application(application)
                self.repository.flush()
                self.repository.commit()
                return RegistrationResult(
                    result_type="Application",
                    user=None,
                    application=application,
                )

            self.repository.commit()
            return RegistrationResult(result_type="User", user=user, application=None)
        except IntegrityError as exc:
            self.repository.rollback()
            raise _unique_conflict() from exc

    def login(self, command: LoginCommand) -> TokenIssueResult:
        user = self.repository.find_user_by_login(command.login)
        if user is None:
            if self.repository.has_pending_registration_for_login(command.login):
                raise _user_pending_approval()
            raise _invalid_credentials()

        if not verify_password(command.password, user.password_hash):
            raise _invalid_credentials()

        self._ensure_user_can_receive_token(user)
        return self._issue_token_pair(
            user=user,
            user_agent=command.user_agent,
            ip_address=command.ip_address,
        )

    def refresh(self, refresh_token: str) -> TokenRefreshResult:
        refresh_session = self._get_valid_refresh_session(refresh_token)
        user = self.repository.find_user_by_id(refresh_session.user_id)
        if user is None:
            raise _refresh_session_invalid()

        self._ensure_user_can_receive_token(user)
        access_token, access_token_expires_at = create_access_token(
            user_id=user.user_id,
            role=user.role,
            status=user.status,
            settings=self.settings,
        )
        return TokenRefreshResult(
            access_token=access_token,
            access_token_expires_at=access_token_expires_at,
            refresh_token=refresh_token,
            refresh_session=refresh_session,
            user=user,
        )

    def logout(self, refresh_token: str) -> LogoutResult:
        refresh_session = self._get_valid_refresh_session(refresh_token)
        revoked_at = _utc_now()
        refresh_session.revoked_at = revoked_at
        self.repository.commit()
        return LogoutResult(
            success=True,
            refresh_session_id=refresh_session.refresh_session_id,
            revoked_at=revoked_at,
        )

    def get_current_user(self, access_token: str) -> UserAccount:
        from vbank.shared.security import decode_access_token

        claims = decode_access_token(access_token, self.settings)
        user = self.repository.find_user_by_id(claims.user_id)
        if user is None:
            raise VBankError(
                code="OBJECT_NOT_FOUND",
                message="Пользователь не найден",
                status_code=404,
                details={"category": "object_state"},
            )

        if user.status == "Blocked":
            raise _user_blocked()
        if self.repository.has_pending_registration_for_user(user.user_id):
            raise _user_pending_approval()

        return user

    def _issue_token_pair(
        self,
        *,
        user: UserAccount,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenIssueResult:
        now = _utc_now()
        access_token, access_token_expires_at = create_access_token(
            user_id=user.user_id,
            role=user.role,
            status=user.status,
            settings=self.settings,
            issued_at=now,
        )
        refresh_token = create_refresh_token()
        refresh_session = RefreshSession(
            refresh_session_id=uuid4(),
            user_id=user.user_id,
            token_hash=hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=self.settings.refresh_token_ttl_days),
            revoked_at=None,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        try:
            self.repository.add_refresh_session(refresh_session)
            self.repository.flush()
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise VBankError(
                code="INTERNAL_ERROR",
                message="Не удалось создать refresh-сессию",
                status_code=500,
                details={"category": "internal"},
            ) from exc

        return TokenIssueResult(
            access_token=access_token,
            access_token_expires_at=access_token_expires_at,
            refresh_token=refresh_token,
            refresh_session=refresh_session,
            user=user,
        )

    def _get_valid_refresh_session(self, refresh_token: str) -> RefreshSession:
        refresh_session = self.repository.find_refresh_session_by_token_hash(
            hash_refresh_token(refresh_token)
        )
        if refresh_session is None:
            raise _refresh_session_invalid()
        if refresh_session.revoked_at is not None:
            raise _refresh_session_invalid()
        if refresh_session.expires_at <= _utc_now():
            raise _refresh_session_invalid()
        return refresh_session

    def _ensure_identity_is_available(self, command: RegisterUserCommand) -> None:
        if self.repository.identity_exists(
            email=command.email,
            username=command.username,
            phone_number=command.phone_number,
        ):
            raise _unique_conflict()
        if self.repository.pending_registration_identity_exists(
            email=command.email,
            username=command.username,
            phone_number=command.phone_number,
        ):
            raise _unique_conflict()

    def _ensure_user_can_receive_token(self, user: UserAccount) -> None:
        if user.status == "Blocked":
            raise _user_blocked()
        if self.repository.has_pending_registration_for_user(user.user_id):
            raise _user_pending_approval()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _invalid_credentials() -> VBankError:
    return VBankError(
        code="INVALID_CREDENTIALS",
        message="Логин или пароль неверны",
        status_code=401,
        details={"category": "access"},
    )


def _refresh_session_invalid() -> VBankError:
    return VBankError(
        code="REFRESH_SESSION_INVALID",
        message="Refresh-сессия недействительна",
        status_code=401,
        details={"category": "access"},
    )


def _user_blocked() -> VBankError:
    return VBankError(
        code="USER_BLOCKED",
        message="Пользователь заблокирован",
        status_code=403,
        details={"category": "access"},
    )


def _user_pending_approval() -> VBankError:
    return VBankError(
        code="USER_PENDING_APPROVAL",
        message="Регистрация пользователя ожидает одобрения",
        status_code=409,
        details={"category": "object_state"},
    )


def _unique_conflict() -> VBankError:
    return VBankError(
        code="UNIQUE_CONFLICT",
        message="Пользователь с такими данными уже существует",
        status_code=409,
        details={"category": "business_rule"},
    )
