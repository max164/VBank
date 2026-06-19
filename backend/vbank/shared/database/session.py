from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from vbank.shared.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings | None = None) -> Engine:
    resolved_settings = settings or get_settings()
    return create_engine(
        resolved_settings.database_url,
        echo=resolved_settings.database_echo,
        pool_pre_ping=True,
    )


def build_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=build_engine(settings),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

