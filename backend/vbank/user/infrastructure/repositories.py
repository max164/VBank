from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vbank.dictionary.infrastructure.models import ReasonCode
from vbank.user.infrastructure.models import UserAccount


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[UserAccount]:
        return list(
            self.session.scalars(
                self._filtered_select(role=role, status=status)
                .order_by(UserAccount.registered_at.desc(), UserAccount.user_id)
                .limit(limit)
                .offset(offset)
            )
        )

    def count_users(self, *, role: str | None, status: str | None) -> int:
        return int(
            self.session.scalar(
                self._filtered_select(role=role, status=status)
                .with_only_columns(func.count())
                .order_by(None)
            )
            or 0
        )

    def find_user_by_id(self, user_id: UUID) -> UserAccount | None:
        return self.session.get(UserAccount, user_id)

    def reason_code_allows_user_change(self, reason_code: str) -> bool:
        return (
            self.session.scalar(
                select(ReasonCode.reason_code)
                .where(
                    ReasonCode.reason_code == reason_code,
                    ReasonCode.status == "Active",
                    ReasonCode.scope.in_(("User", "Both")),
                )
                .limit(1)
            )
            is not None
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def _filtered_select(self, *, role: str | None, status: str | None):
        statement = select(UserAccount)
        if role is not None:
            statement = statement.where(UserAccount.role == role)
        if status is not None:
            statement = statement.where(UserAccount.status == status)
        return statement
