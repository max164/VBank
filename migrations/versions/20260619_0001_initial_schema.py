"""Create initial VBank storage schema.

Revision ID: 20260619_0001
Revises:
Create Date: 2026-06-19 00:00:00.000000
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260619_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_COLUMN_TYPES = {
    "currency_id": postgresql.UUID(as_uuid=True),
    "setting_id": postgresql.UUID(as_uuid=True),
    "precision": sa.Integer(),
    "allow_negative_balance": sa.Boolean(),
    "updated_at": sa.DateTime(timezone=True),
}


def upgrade() -> None:
    create_tables()
    create_indexes()
    seed_initial_reference_data()


def downgrade() -> None:
    raise RuntimeError("VBank migrations are forward-only")


def create_tables() -> None:
    op.create_table(
        "user_account",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role in ('Client','Operator','Admin')", name="ck_user_account_role"),
        sa.CheckConstraint("status in ('Active','Blocked')", name="ck_user_account_status"),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_account"),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
        sa.UniqueConstraint("phone_number", name="uq_user_account_phone_number"),
        sa.UniqueConstraint("username", name="uq_user_account_username"),
    )

    op.create_table(
        "currency",
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("precision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.CheckConstraint("precision between 2 and 10", name="ck_currency_precision"),
        sa.CheckConstraint("status in ('Active','Disabled')", name="ck_currency_status"),
        sa.PrimaryKeyConstraint("currency_id", name="pk_currency"),
        sa.UniqueConstraint("currency_code", name="uq_currency_currency_code"),
    )

    op.create_table(
        "account_type",
        sa.Column("account_type_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("allow_negative_balance", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.CheckConstraint("status in ('Active','Disabled')", name="ck_account_type_status"),
        sa.PrimaryKeyConstraint("account_type_code", name="pk_account_type"),
    )

    op.create_table(
        "reason_code",
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "scope in ('Request','Transaction','User','Both')",
            name="ck_reason_code_scope",
        ),
        sa.CheckConstraint("status in ('Active','Disabled')", name="ck_reason_code_status"),
        sa.PrimaryKeyConstraint("reason_code", name="pk_reason_code"),
    )

    op.create_table(
        "system_setting",
        sa.Column("setting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "key in ("
            "'bank_name',"
            "'registration_mode',"
            "'account_opening_mode',"
            "'internal_transfer_mode',"
            "'cash_in_out_mode'"
            ")",
            name="ck_system_setting_key",
        ),
        sa.CheckConstraint(
            "value_type in ('string','mode')",
            name="ck_system_setting_value_type",
        ),
        sa.CheckConstraint(
            "(key <> 'bank_name' or (value_type = 'string' and value <> ''))",
            name="ck_system_setting_bank_name",
        ),
        sa.CheckConstraint(
            "(key <> 'registration_mode' "
            "or (value_type = 'mode' and value in ('auto','manual')))",
            name="ck_system_setting_registration_mode",
        ),
        sa.CheckConstraint(
            "(key <> 'account_opening_mode' "
            "or (value_type = 'mode' and value in ('auto','manual')))",
            name="ck_system_setting_account_opening_mode",
        ),
        sa.CheckConstraint(
            "(key <> 'internal_transfer_mode' "
            "or (value_type = 'mode' and value in ('enabled','manual','disabled')))",
            name="ck_system_setting_internal_transfer_mode",
        ),
        sa.CheckConstraint(
            "(key <> 'cash_in_out_mode' "
            "or (value_type = 'mode' and value in ('manual','disabled')))",
            name="ck_system_setting_cash_in_out_mode",
        ),
        sa.PrimaryKeyConstraint("setting_id", name="pk_system_setting"),
        sa.UniqueConstraint("key", name="uq_system_setting_key"),
    )

    op.create_table(
        "account",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_number", sa.CHAR(length=20), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_type_code", sa.String(length=32), nullable=False),
        sa.Column("balance", sa.Numeric(precision=38, scale=10), nullable=False),
        sa.Column("negative_balance_limit", sa.Numeric(precision=38, scale=10), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("account_number ~ '^[0-9]{20}$'", name="ck_account_account_number"),
        sa.CheckConstraint(
            "status in ('Active','Blocked','Closed')",
            name="ck_account_status",
        ),
        sa.CheckConstraint(
            "negative_balance_limit is null or negative_balance_limit >= 0",
            name="ck_account_negative_balance_limit",
        ),
        sa.CheckConstraint(
            "balance >= 0 "
            "or (negative_balance_limit is not null and balance >= -negative_balance_limit)",
            name="ck_account_balance_floor",
        ),
        sa.CheckConstraint(
            "(status = 'Closed') = (closed_at is not null)",
            name="ck_account_closed_at",
        ),
        sa.CheckConstraint(
            "status <> 'Closed' or balance = 0",
            name="ck_account_closed_balance_zero",
        ),
        sa.ForeignKeyConstraint(
            ["account_type_code"],
            ["account_type.account_type_code"],
            name="fk_account_account_type_code_account_type",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currency.currency_id"],
            name="fk_account_currency_id_currency",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.user_id"],
            name="fk_account_user_id_user_account",
        ),
        sa.PrimaryKeyConstraint("account_id", name="pk_account"),
        sa.UniqueConstraint("account_number", name="uq_account_account_number"),
        sa.UniqueConstraint(
            "user_id",
            "currency_id",
            "account_type_code",
            name="uq_account_user_currency_type",
        ),
    )

    op.create_table(
        "transaction_record",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("from_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=38, scale=10), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("initiator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "transaction_type in ('Transfer','Deposit','Withdraw','Compensation')",
            name="ck_transaction_record_transaction_type",
        ),
        sa.CheckConstraint(
            "status in ('Success','Rejected')",
            name="ck_transaction_record_status",
        ),
        sa.CheckConstraint("amount > 0", name="ck_transaction_record_amount_positive"),
        sa.CheckConstraint(
            "from_account_id is not null or to_account_id is not null",
            name="ck_transaction_record_any_account",
        ),
        sa.CheckConstraint(
            "from_account_id is null or to_account_id is null "
            "or from_account_id <> to_account_id",
            name="ck_transaction_record_distinct_accounts",
        ),
        sa.CheckConstraint(
            "transaction_type <> 'Deposit' "
            "or (from_account_id is null and to_account_id is not null)",
            name="ck_transaction_record_deposit_shape",
        ),
        sa.CheckConstraint(
            "transaction_type <> 'Withdraw' "
            "or (from_account_id is not null and to_account_id is null)",
            name="ck_transaction_record_withdraw_shape",
        ),
        sa.CheckConstraint(
            "transaction_type <> 'Transfer' "
            "or (from_account_id is not null and to_account_id is not null)",
            name="ck_transaction_record_transfer_shape",
        ),
        sa.CheckConstraint(
            "transaction_type <> 'Compensation' or related_transaction_id is not null",
            name="ck_transaction_record_compensation_related",
        ),
        sa.CheckConstraint(
            "transaction_type = 'Compensation' or related_transaction_id is null",
            name="ck_transaction_record_non_compensation_related",
        ),
        sa.CheckConstraint(
            "related_transaction_id is null or related_transaction_id <> transaction_id",
            name="ck_transaction_record_related_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currency.currency_id"],
            name="fk_transaction_record_currency_id_currency",
        ),
        sa.ForeignKeyConstraint(
            ["from_account_id"],
            ["account.account_id"],
            name="fk_transaction_record_from_account_id_account",
        ),
        sa.ForeignKeyConstraint(
            ["initiator_user_id"],
            ["user_account.user_id"],
            name="fk_transaction_record_initiator_user_id_user_account",
        ),
        sa.ForeignKeyConstraint(
            ["reason_code"],
            ["reason_code.reason_code"],
            name="fk_transaction_record_reason_code_reason_code",
        ),
        sa.ForeignKeyConstraint(
            ["related_transaction_id"],
            ["transaction_record.transaction_id"],
            name="fk_transaction_record_related_transaction_id_transaction_record",
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"],
            ["account.account_id"],
            name="fk_transaction_record_to_account_id_account",
        ),
        sa.PrimaryKeyConstraint("transaction_id", name="pk_transaction_record"),
    )

    op.create_table(
        "request",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("initiator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("result_entity_type", sa.String(length=32), nullable=True),
        sa.Column("result_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "request_type in ('UserRegistration','AccountOpening','Deposit','Withdraw','Transfer')",
            name="ck_request_request_type",
        ),
        sa.CheckConstraint(
            "status in ('PendingApproval','Approved','Rejected')",
            name="ck_request_status",
        ),
        sa.CheckConstraint(
            "result_entity_type is null or result_entity_type in ('User','Account','Transaction')",
            name="ck_request_result_entity_type",
        ),
        sa.CheckConstraint(
            "(result_entity_type is null) = (result_entity_id is null)",
            name="ck_request_result_entity_pair",
        ),
        sa.CheckConstraint(
            "(status = 'PendingApproval') = (decided_at is null)",
            name="ck_request_pending_decided_at",
        ),
        sa.CheckConstraint(
            "status <> 'PendingApproval' "
            "or (operator_user_id is null and reason_code is null and result_entity_type is null)",
            name="ck_request_pending_has_no_decision",
        ),
        sa.CheckConstraint(
            "status = 'PendingApproval' "
            "or (operator_user_id is not null and reason_code is not null)",
            name="ck_request_decided_has_operator_reason",
        ),
        sa.CheckConstraint(
            "status <> 'Approved' or result_entity_type is not null",
            name="ck_request_approved_has_result",
        ),
        sa.CheckConstraint(
            "status <> 'Rejected' or result_entity_type is null",
            name="ck_request_rejected_has_no_result",
        ),
        sa.ForeignKeyConstraint(
            ["initiator_user_id"],
            ["user_account.user_id"],
            name="fk_request_initiator_user_id_user_account",
        ),
        sa.ForeignKeyConstraint(
            ["operator_user_id"],
            ["user_account.user_id"],
            name="fk_request_operator_user_id_user_account",
        ),
        sa.ForeignKeyConstraint(
            ["reason_code"],
            ["reason_code.reason_code"],
            name="fk_request_reason_code_reason_code",
        ),
        sa.PrimaryKeyConstraint("request_id", name="pk_request"),
    )

    op.create_table(
        "ledger_entry",
        sa.Column("ledger_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=38, scale=10), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount <> 0", name="ck_ledger_entry_amount_not_zero"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["account.account_id"],
            name="fk_ledger_entry_account_id_account",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currency.currency_id"],
            name="fk_ledger_entry_currency_id_currency",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transaction_record.transaction_id"],
            name="fk_ledger_entry_transaction_id_transaction_record",
        ),
        sa.PrimaryKeyConstraint("ledger_entry_id", name="pk_ledger_entry"),
    )

    op.create_table(
        "refresh_session",
        sa.Column("refresh_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.user_id"],
            name="fk_refresh_session_user_id_user_account",
        ),
        sa.PrimaryKeyConstraint("refresh_session_id", name="pk_refresh_session"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_session_token_hash"),
    )

    op.create_table(
        "audit_log",
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actor_type in ('User','Operator','Admin','System')",
            name="ck_audit_log_actor_type",
        ),
        sa.PrimaryKeyConstraint("audit_id", name="pk_audit_log"),
    )

    op.create_table(
        "idempotency_entry",
        sa.Column("idempotency_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_scope", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "idempotency_scope <> ''",
            name="ck_idempotency_entry_scope_not_empty",
        ),
        sa.PrimaryKeyConstraint("idempotency_entry_id", name="pk_idempotency_entry"),
        sa.UniqueConstraint(
            "idempotency_scope",
            "endpoint",
            "idempotency_key",
            name="uq_idempotency_entry_scope_endpoint_key",
        ),
    )


def create_indexes() -> None:
    op.create_index("ix_user_account_role", "user_account", ["role"])
    op.create_index("ix_user_account_status", "user_account", ["status"])
    op.create_index("ix_account_user_id", "account", ["user_id"])
    op.create_index("ix_account_status", "account", ["status"])
    op.create_index(
        "ix_transaction_record_initiator_user_id",
        "transaction_record",
        ["initiator_user_id"],
    )
    op.create_index(
        "ix_transaction_record_from_account_id",
        "transaction_record",
        ["from_account_id"],
    )
    op.create_index(
        "ix_transaction_record_to_account_id",
        "transaction_record",
        ["to_account_id"],
    )
    op.create_index("ix_transaction_record_created_at", "transaction_record", ["created_at"])
    op.create_index(
        "ix_transaction_record_related_transaction_id",
        "transaction_record",
        ["related_transaction_id"],
    )
    op.create_index(
        "ix_ledger_entry_account_id_created_at",
        "ledger_entry",
        ["account_id", "created_at"],
    )
    op.create_index("ix_ledger_entry_transaction_id", "ledger_entry", ["transaction_id"])
    op.create_index("ix_request_initiator_user_id", "request", ["initiator_user_id"])
    op.create_index("ix_request_operator_user_id", "request", ["operator_user_id"])
    op.create_index("ix_request_status_created_at", "request", ["status", "created_at"])
    op.create_index("ix_request_request_type", "request", ["request_type"])
    op.create_index(
        "ix_request_result_entity",
        "request",
        ["result_entity_type", "result_entity_id"],
    )
    op.create_index(
        "ix_audit_log_actor_id_created_at",
        "audit_log",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "ix_audit_log_action_type_created_at",
        "audit_log",
        ["action_type", "created_at"],
    )
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index("ix_idempotency_entry_created_at", "idempotency_entry", ["created_at"])
    op.create_index("ix_refresh_session_user_id", "refresh_session", ["user_id"])
    op.create_index("ix_refresh_session_expires_at", "refresh_session", ["expires_at"])


def seed_initial_reference_data() -> None:
    seed_timestamp = datetime(2026, 6, 19, tzinfo=UTC)

    upsert_records(
        "currency",
        ["currency_code"],
        ["currency_id", "currency_code", "name", "precision", "status"],
        [
            {
                "currency_id": UUID("d2d907b5-70f5-4d39-a3f3-01f42e8c68dd"),
                "currency_code": "RUB",
                "name": "Российский рубль",
                "precision": 2,
                "status": "Active",
            },
        ],
    )
    upsert_records(
        "account_type",
        ["account_type_code"],
        ["account_type_code", "name", "allow_negative_balance", "status"],
        [
            {
                "account_type_code": "CURRENT",
                "name": "Текущий счёт",
                "allow_negative_balance": False,
                "status": "Active",
            },
            {
                "account_type_code": "CREDIT",
                "name": "Кредитный счёт",
                "allow_negative_balance": True,
                "status": "Active",
            },
        ],
    )
    upsert_records(
        "reason_code",
        ["reason_code"],
        ["reason_code", "name", "description", "scope", "status"],
        [
            {
                "reason_code": "CLIENT_REQUEST",
                "name": "Запрос клиента",
                "description": "Решение принято по обращению клиента.",
                "scope": "Request",
                "status": "Active",
            },
            {
                "reason_code": "APPROVED_BY_OPERATOR",
                "name": "Одобрено оператором",
                "description": "Оператор одобрил заявку после проверки.",
                "scope": "Request",
                "status": "Active",
            },
            {
                "reason_code": "REJECTED_BY_OPERATOR",
                "name": "Отклонено оператором",
                "description": "Оператор отклонил заявку после проверки.",
                "scope": "Request",
                "status": "Active",
            },
            {
                "reason_code": "OPERATOR_CORRECTION",
                "name": "Корректировка оператором",
                "description": "Оператор создаёт корректирующую компенсацию.",
                "scope": "Transaction",
                "status": "Active",
            },
            {
                "reason_code": "SECURITY_REVIEW",
                "name": "Проверка безопасности",
                "description": "Статус пользователя изменён после проверки безопасности.",
                "scope": "User",
                "status": "Active",
            },
        ],
    )
    upsert_records(
        "system_setting",
        ["key"],
        ["setting_id", "key", "value", "value_type", "description", "updated_at"],
        [
            {
                "setting_id": UUID("04b646cb-1f4d-4f95-b353-2f7fd826edfb"),
                "key": "bank_name",
                "value": "VBank",
                "value_type": "string",
                "description": "Отображаемое имя системы.",
                "updated_at": seed_timestamp,
            },
            {
                "setting_id": UUID("75c62702-f2e1-47f8-bcf7-d6d7dbb3e9a0"),
                "key": "registration_mode",
                "value": "auto",
                "value_type": "mode",
                "description": "Регистрация пользователя создаёт Client без ручной заявки.",
                "updated_at": seed_timestamp,
            },
            {
                "setting_id": UUID("a82a2774-f39c-4dd6-9ff3-53c79f400f2f"),
                "key": "account_opening_mode",
                "value": "auto",
                "value_type": "mode",
                "description": "Открытие счёта через POST /accounts создаёт счёт сразу.",
                "updated_at": seed_timestamp,
            },
            {
                "setting_id": UUID("6be06937-c0ea-4936-aa8d-3f5ec21c4957"),
                "key": "internal_transfer_mode",
                "value": "enabled",
                "value_type": "mode",
                "description": "Внутренний перевод выполняется напрямую.",
                "updated_at": seed_timestamp,
            },
            {
                "setting_id": UUID("ab3bb372-dfad-468a-9f17-81c7404f56e5"),
                "key": "cash_in_out_mode",
                "value": "manual",
                "value_type": "mode",
                "description": "Пополнение и вывод доступны только через заявку.",
                "updated_at": seed_timestamp,
            },
        ],
    )


def upsert_records(
    table_name: str,
    key_columns: list[str],
    columns: list[str],
    records: list[Mapping[str, object]],
) -> None:
    table = sa.table(
        table_name,
        *(sa.column(column, SEED_COLUMN_TYPES.get(column, sa.String())) for column in columns),
    )
    statement = postgresql.insert(table).values(records)
    update_columns = {
        column: getattr(statement.excluded, column)
        for column in columns
        if column not in key_columns
    }
    op.execute(
        statement.on_conflict_do_update(
            index_elements=key_columns,
            set_=update_columns,
        )
    )
