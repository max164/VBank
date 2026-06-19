from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class Currency(Base):
    __tablename__ = "currency"
    __table_args__ = (
        UniqueConstraint("currency_code", name="uq_currency_currency_code"),
        CheckConstraint("precision between 2 and 10", name="ck_currency_precision"),
        CheckConstraint("status in ('Active','Disabled')", name="ck_currency_status"),
    )

    currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    precision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class AccountType(Base):
    __tablename__ = "account_type"
    __table_args__ = (
        CheckConstraint("status in ('Active','Disabled')", name="ck_account_type_status"),
    )

    account_type_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    allow_negative_balance: Mapped[bool] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class ReasonCode(Base):
    __tablename__ = "reason_code"
    __table_args__ = (
        CheckConstraint(
            "scope in ('Request','Transaction','User','Both')",
            name="ck_reason_code_scope",
        ),
        CheckConstraint("status in ('Active','Disabled')", name="ck_reason_code_status"),
    )

    reason_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
