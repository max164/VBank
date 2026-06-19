from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vbank.auth.infrastructure.models import RefreshSession
from vbank.request.infrastructure.models import Request
from vbank.setting.infrastructure.models import SystemSetting
from vbank.user.infrastructure.models import UserAccount


class SqlAlchemyAuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_system_setting(self, key: str) -> str | None:
        return self.session.scalar(
            select(SystemSetting.value).where(SystemSetting.key == key).limit(1)
        )

    def identity_exists(self, *, email: str, username: str, phone_number: str) -> bool:
        return (
            self.session.scalar(
                select(UserAccount.user_id)
                .where(
                    or_(
                        UserAccount.email == email,
                        UserAccount.username == username,
                        UserAccount.phone_number == phone_number,
                    )
                )
                .limit(1)
            )
            is not None
        )

    def pending_registration_identity_exists(
        self,
        *,
        email: str,
        username: str,
        phone_number: str,
    ) -> bool:
        return (
            self.session.scalar(
                select(Request.request_id)
                .where(
                    Request.request_type == "UserRegistration",
                    Request.status == "PendingApproval",
                    or_(
                        Request.payload["email"].as_string() == email,
                        Request.payload["username"].as_string() == username,
                        Request.payload["phone_number"].as_string() == phone_number,
                    ),
                )
                .limit(1)
            )
            is not None
        )

    def find_user_by_login(self, login: str) -> UserAccount | None:
        return self.session.scalar(
            select(UserAccount)
            .where(
                or_(
                    UserAccount.email == login,
                    UserAccount.username == login,
                    UserAccount.phone_number == login,
                )
            )
            .limit(1)
        )

    def find_user_by_id(self, user_id: UUID) -> UserAccount | None:
        return self.session.get(UserAccount, user_id)

    def has_pending_registration_for_user(self, user_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(Request.request_id)
                .where(
                    Request.request_type == "UserRegistration",
                    Request.status == "PendingApproval",
                    Request.initiator_user_id == user_id,
                )
                .limit(1)
            )
            is not None
        )

    def has_pending_registration_for_login(self, login: str) -> bool:
        return (
            self.session.scalar(
                select(Request.request_id)
                .where(
                    Request.request_type == "UserRegistration",
                    Request.status == "PendingApproval",
                    or_(
                        Request.payload["email"].as_string() == login,
                        Request.payload["username"].as_string() == login,
                        Request.payload["phone_number"].as_string() == login,
                    ),
                )
                .limit(1)
            )
            is not None
        )

    def find_refresh_session_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        return self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .limit(1)
        )

    def add_user(self, user: UserAccount) -> None:
        self.session.add(user)

    def add_application(self, application: Request) -> None:
        self.session.add(application)

    def add_refresh_session(self, refresh_session: RefreshSession) -> None:
        self.session.add(refresh_session)

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
