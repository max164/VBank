from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (
        UniqueConstraint("account_number", name="uq_account_account_number"),
        UniqueConstraint(
            "user_id",
            "currency_id",
            "account_type_code",
            name="uq_account_user_currency_type",
        ),
        CheckConstraint("account_number ~ '^[0-9]{20}$'", name="ck_account_account_number"),
        CheckConstraint(
            "status in ('Active','Blocked','Closed')",
            name="ck_account_status",
        ),
        CheckConstraint(
            "negative_balance_limit is null or negative_balance_limit >= 0",
            name="ck_account_negative_balance_limit",
        ),
        CheckConstraint(
            "balance >= 0 "
            "or (negative_balance_limit is not null and balance >= -negative_balance_limit)",
            name="ck_account_balance_floor",
        ),
        CheckConstraint(
            "(status = 'Closed') = (closed_at is not null)",
            name="ck_account_closed_at",
        ),
        CheckConstraint(
            "status <> 'Closed' or balance = 0",
            name="ck_account_closed_balance_zero",
        ),
        Index("ix_account_user_id", "user_id"),
        Index("ix_account_status", "status"),
    )

    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    account_number: Mapped[str] = mapped_column(CHAR(20), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_account.user_id", name="fk_account_user_id_user_account"),
        nullable=False,
    )
    currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("currency.currency_id", name="fk_account_currency_id_currency"),
        nullable=False,
    )
    account_type_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey(
            "account_type.account_type_code",
            name="fk_account_account_type_code_account_type",
        ),
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(38, 10), nullable=False)
    negative_balance_limit: Mapped[Decimal | None] = mapped_column(Numeric(38, 10))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
