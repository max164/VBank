from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Table

from vbank.dictionary.infrastructure.models import AccountType, Currency, ReasonCode
from vbank.setting.infrastructure.models import SystemSetting

INITIAL_TIMESTAMP = datetime(2026, 6, 19, tzinfo=UTC)

INITIAL_CURRENCIES: tuple[dict[str, object], ...] = (
    {
        "currency_id": UUID("d2d907b5-70f5-4d39-a3f3-01f42e8c68dd"),
        "currency_code": "RUB",
        "name": "Российский рубль",
        "precision": 2,
        "status": "Active",
    },
)

INITIAL_ACCOUNT_TYPES: tuple[dict[str, object], ...] = (
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
)

INITIAL_REASON_CODES: tuple[dict[str, object], ...] = (
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
)

INITIAL_SYSTEM_SETTINGS: tuple[dict[str, object], ...] = (
    {
        "setting_id": UUID("04b646cb-1f4d-4f95-b353-2f7fd826edfb"),
        "key": "bank_name",
        "value": "VBank",
        "value_type": "string",
        "description": "Отображаемое имя системы.",
        "updated_at": INITIAL_TIMESTAMP,
    },
    {
        "setting_id": UUID("75c62702-f2e1-47f8-bcf7-d6d7dbb3e9a0"),
        "key": "registration_mode",
        "value": "auto",
        "value_type": "mode",
        "description": "Регистрация пользователя создаёт Client без ручной заявки.",
        "updated_at": INITIAL_TIMESTAMP,
    },
    {
        "setting_id": UUID("a82a2774-f39c-4dd6-9ff3-53c79f400f2f"),
        "key": "account_opening_mode",
        "value": "auto",
        "value_type": "mode",
        "description": "Открытие счёта через POST /accounts создаёт счёт сразу.",
        "updated_at": INITIAL_TIMESTAMP,
    },
    {
        "setting_id": UUID("6be06937-c0ea-4936-aa8d-3f5ec21c4957"),
        "key": "internal_transfer_mode",
        "value": "enabled",
        "value_type": "mode",
        "description": "Внутренний перевод выполняется напрямую.",
        "updated_at": INITIAL_TIMESTAMP,
    },
    {
        "setting_id": UUID("ab3bb372-dfad-468a-9f17-81c7404f56e5"),
        "key": "cash_in_out_mode",
        "value": "manual",
        "value_type": "mode",
        "description": "Пополнение и вывод доступны только через заявку.",
        "updated_at": INITIAL_TIMESTAMP,
    },
)


def seed_initial_reference_data(session: Session) -> None:
    upsert_records(session, Currency.__table__, ["currency_code"], INITIAL_CURRENCIES)
    upsert_records(
        session,
        AccountType.__table__,
        ["account_type_code"],
        INITIAL_ACCOUNT_TYPES,
    )
    upsert_records(session, ReasonCode.__table__, ["reason_code"], INITIAL_REASON_CODES)
    upsert_records(session, SystemSetting.__table__, ["key"], INITIAL_SYSTEM_SETTINGS)


def upsert_records(
    session: Session,
    table: Table,
    key_columns: list[str],
    records: Iterable[Mapping[str, Any]],
) -> None:
    values = [dict(record) for record in records]
    if not values:
        return

    statement = insert(table).values(values)
    update_columns = {
        column.name: getattr(statement.excluded, column.name)
        for column in table.columns
        if column.name not in key_columns
    }
    session.execute(
        statement.on_conflict_do_update(
            index_elements=key_columns,
            set_=update_columns,
        )
    )
