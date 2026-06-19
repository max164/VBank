from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from vbank.shared.api.dependencies import get_session
from vbank.user.application.service import UserService
from vbank.user.infrastructure.repositories import SqlAlchemyUserRepository


def get_user_service(
    session: Annotated[Session, Depends(get_session)],
) -> UserService:
    return UserService(SqlAlchemyUserRepository(session))
