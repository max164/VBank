from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class TransactionRecord(Base):
    __tablename__ = "transaction_record"
    __table_args__ = (
        CheckConstraint(
            "transaction_type in ('Transfer','Deposit','Withdraw','Compensation')",
            name="ck_transaction_record_transaction_type",
        ),
        CheckConstraint(
            "status in ('Success','Rejected')",
            name="ck_transaction_record_status",
        ),
        CheckConstraint("amount > 0", name="ck_transaction_record_amount_positive"),
        CheckConstraint(
            "from_account_id is not null or to_account_id is not null",
            name="ck_transaction_record_any_account",
        ),
        CheckConstraint(
            "from_account_id is null or to_account_id is null "
            "or from_account_id <> to_account_id",
            name="ck_transaction_record_distinct_accounts",
        ),
        CheckConstraint(
            "transaction_type <> 'Deposit' "
            "or (from_account_id is null and to_account_id is not null)",
            name="ck_transaction_record_deposit_shape",
        ),
        CheckConstraint(
            "transaction_type <> 'Withdraw' "
            "or (from_account_id is not null and to_account_id is null)",
            name="ck_transaction_record_withdraw_shape",
        ),
        CheckConstraint(
            "transaction_type <> 'Transfer' "
            "or (from_account_id is not null and to_account_id is not null)",
            name="ck_transaction_record_transfer_shape",
        ),
        CheckConstraint(
            "transaction_type <> 'Compensation' or related_transaction_id is not null",
            name="ck_transaction_record_compensation_related",
        ),
        CheckConstraint(
            "transaction_type = 'Compensation' or related_transaction_id is null",
            name="ck_transaction_record_non_compensation_related",
        ),
        CheckConstraint(
            "related_transaction_id is null or related_transaction_id <> transaction_id",
            name="ck_transaction_record_related_not_self",
        ),
        Index("ix_transaction_record_initiator_user_id", "initiator_user_id"),
        Index("ix_transaction_record_from_account_id", "from_account_id"),
        Index("ix_transaction_record_to_account_id", "to_account_id"),
        Index("ix_transaction_record_created_at", "created_at"),
        Index("ix_transaction_record_related_transaction_id", "related_transaction_id"),
    )

    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("account.account_id", name="fk_transaction_record_from_account_id_account"),
    )
    to_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("account.account_id", name="fk_transaction_record_to_account_id_account"),
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 10), nullable=False)
    currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("currency.currency_id", name="fk_transaction_record_currency_id_currency"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(
            "reason_code.reason_code",
            name="fk_transaction_record_reason_code_reason_code",
        ),
    )
    initiator_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "user_account.user_id",
            name="fk_transaction_record_initiator_user_id_user_account",
        ),
        nullable=False,
    )
    related_transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "transaction_record.transaction_id",
            name="fk_transaction_record_related_transaction_id_transaction_record",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LedgerEntry(Base):
    __tablename__ = "ledger_entry"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_ledger_entry_amount_not_zero"),
        Index("ix_ledger_entry_account_id_created_at", "account_id", "created_at"),
        Index("ix_ledger_entry_transaction_id", "transaction_id"),
    )

    ledger_entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("account.account_id", name="fk_ledger_entry_account_id_account"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 10), nullable=False)
    currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("currency.currency_id", name="fk_ledger_entry_currency_id_currency"),
        nullable=False,
    )
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "transaction_record.transaction_id",
            name="fk_ledger_entry_transaction_id_transaction_record",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
