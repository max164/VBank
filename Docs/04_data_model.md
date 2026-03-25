# VBank — модель данных

## 1. Общие правила хранения

* СУБД: PostgreSQL.
* Идентификаторы сущностей: `uuid`.
* Денежные значения: `numeric(38,10)`.
* Все временные метки: `timestamptz` в UTC.
* Имена таблиц и полей: `snake_case`.
* Доменные записи не удаляются физически; применяется статус или отзыв.

## 2. Таблицы

### 2.1. `user_account`

**Назначение:** пользователи системы.

**Поля:**

* `user_id uuid pk`
* `email varchar(...) not null unique`
* `username varchar(...) not null unique`
* `phone_number varchar(...) not null unique`
* `password_hash varchar(...) not null`
* `role varchar(...) not null`
* `status varchar(...) not null`
* `registered_at timestamptz not null`

**Ограничения:**

* `role in ('Client','Operator','Admin')`
* `status in ('Active','Blocked')`

**Индексы:**

* `ix_user_account_role`
* `ix_user_account_status`

### 2.2. `currency`

**Назначение:** валюты.

**Поля:**

* `currency_id uuid pk`
* `currency_code varchar(3) not null unique`
* `name varchar(...) not null`
* `precision integer not null`
* `status varchar(...) not null`

**Ограничения:**

* `precision between 2 and 10`
* `status in ('Active','Disabled')`

### 2.3. `account_type`

**Назначение:** типы счетов.

**Поля:**

* `account_type_code varchar(...) pk`
* `name varchar(...) not null`
* `allow_negative_balance boolean not null`
* `status varchar(...) not null`

**Ограничения:**

* `status in ('Active','Disabled')`

### 2.4. `account`

**Назначение:** счета пользователей.

**Поля:**

* `account_id uuid pk`
* `account_number char(20) not null unique`
* `user_id uuid not null fk -> user_account.user_id`
* `currency_id uuid not null fk -> currency.currency_id`
* `account_type_code varchar(...) not null fk -> account_type.account_type_code`
* `balance numeric(38,10) not null`
* `negative_balance_limit numeric(38,10) null`
* `status varchar(...) not null`
* `created_at timestamptz not null`
* `closed_at timestamptz null`

**Ограничения:**

* `status in ('Active','Blocked','Closed')`
* `negative_balance_limit is null or negative_balance_limit >= 0`
* `closed_at is null or status = 'Closed'`
* `unique (user_id, currency_id, account_type_code)`

**Индексы:**

* `ix_account_user_id`
* `ix_account_status`

### 2.5. `transaction_record`

**Назначение:** финансовые операции.

**Поля:**

* `transaction_id uuid pk`
* `transaction_type varchar(...) not null`
* `from_account_id uuid null fk -> account.account_id`
* `to_account_id uuid null fk -> account.account_id`
* `amount numeric(38,10) not null`
* `currency_id uuid not null fk -> currency.currency_id`
* `status varchar(...) not null`
* `reason_code varchar(...) null fk -> reason_code.reason_code`
* `initiator_user_id uuid not null fk -> user_account.user_id`
* `related_transaction_id uuid null fk -> transaction_record.transaction_id`
* `created_at timestamptz not null`
* `completed_at timestamptz null`

**Ограничения:**

* `transaction_type in ('Transfer','Deposit','Withdraw','Compensation')`
* `status in ('Success','Rejected')`
* `amount > 0`
* `from_account_id is not null or to_account_id is not null`

**Индексы:**

* `ix_transaction_record_initiator_user_id`
* `ix_transaction_record_from_account_id`
* `ix_transaction_record_to_account_id`
* `ix_transaction_record_created_at`
* `ix_transaction_record_related_transaction_id`

### 2.6. `ledger_entry`

**Назначение:** проводки.

**Поля:**

* `ledger_entry_id uuid pk`
* `account_id uuid not null fk -> account.account_id`
* `amount numeric(38,10) not null`
* `currency_id uuid not null fk -> currency.currency_id`
* `transaction_id uuid not null fk -> transaction_record.transaction_id`
* `created_at timestamptz not null`

**Индексы:**

* `ix_ledger_entry_account_id_created_at`
* `ix_ledger_entry_transaction_id`

### 2.7. `request`

**Назначение:** ручные заявки.

**Поля:**

* `request_id uuid pk`
* `request_type varchar(...) not null`
* `status varchar(...) not null`
* `initiator_user_id uuid not null fk -> user_account.user_id`
* `operator_user_id uuid null fk -> user_account.user_id`
* `payload jsonb not null`
* `reason_code varchar(...) null fk -> reason_code.reason_code`
* `result_entity_type varchar(...) null`
* `result_entity_id uuid null`
* `created_at timestamptz not null`
* `decided_at timestamptz null`

**Ограничения:**

* `request_type in ('UserRegistration','AccountOpening','Deposit','Withdraw','Transfer')`
* `status in ('PendingApproval','Approved','Rejected')`
* `result_entity_type is null or result_entity_type in ('User','Account','Transaction')`

**Индексы:**

* `ix_request_initiator_user_id`
* `ix_request_operator_user_id`
* `ix_request_status_created_at`
* `ix_request_request_type`
* `ix_request_result_entity`

**Требования к `payload`:**

* `UserRegistration`: `email`, `username`, `phone_number`, `password_hash`
* `AccountOpening`: `currency_id`, `account_type_code`, `negative_balance_limit`
* `Deposit`: `account_id`, `amount`, `currency_id`
* `Withdraw`: `account_id`, `amount`, `currency_id`
* `Transfer`: `from_account_id`, `to_account_number`, `amount`

### 2.8. `reason_code`

**Назначение:** единый справочник причин.

**Поля:**

* `reason_code varchar(...) pk`
* `name varchar(...) not null`
* `description varchar(...) not null`
* `scope varchar(...) not null`
* `status varchar(...) not null`

**Ограничения:**

* `scope in ('Request','Transaction','Both')`
* `status in ('Active','Disabled')`

### 2.9. `system_setting`

**Назначение:** режимы работы системы.

**Поля:**

* `setting_id uuid pk`
* `key varchar(...) not null unique`
* `value varchar(...) not null`
* `value_type varchar(...) not null`
* `description varchar(...) not null`
* `updated_at timestamptz not null`

**Разрешённые ключи:**

* `bank_name`
* `registration_mode`
* `account_opening_mode`
* `internal_transfer_mode`
* `cash_in_out_mode`

### 2.10. `audit_log`

**Назначение:** неизменяемый аудит.

**Поля:**

* `audit_id uuid pk`
* `actor_type varchar(...) not null`
* `actor_id uuid not null`
* `action_type varchar(...) not null`
* `result varchar(...) not null`
* `context jsonb not null`
* `request_id uuid null`
* `created_at timestamptz not null`

**Ограничения:**

* `actor_type in ('User','Operator','Admin','System')`

**Индексы:**

* `ix_audit_log_actor_id_created_at`
* `ix_audit_log_action_type_created_at`
* `ix_audit_log_request_id`

### 2.11. `idempotency_entry`

**Назначение:** хранилище идемпотентности.

**Поля:**

* `idempotency_entry_id uuid pk`
* `actor_id uuid not null`
* `endpoint varchar(...) not null`
* `idempotency_key uuid not null`
* `request_hash varchar(...) not null`
* `response_status integer not null`
* `response_body jsonb not null`
* `created_at timestamptz not null`

**Ограничения:**

* `unique (actor_id, endpoint, idempotency_key)`

**Индексы:**

* `ix_idempotency_entry_created_at`

### 2.12. `refresh_session`

**Назначение:** отзыв `refresh token`.

**Поля:**

* `refresh_session_id uuid pk`
* `user_id uuid not null fk -> user_account.user_id`
* `token_hash varchar(...) not null unique`
* `issued_at timestamptz not null`
* `expires_at timestamptz not null`
* `revoked_at timestamptz null`
* `user_agent varchar(...) null`
* `ip_address varchar(...) null`

**Индексы:**

* `ix_refresh_session_user_id`
* `ix_refresh_session_expires_at`

## 3. Связи

* `user_account 1 -> n account`
* `user_account 1 -> n transaction_record` по `initiator_user_id`
* `user_account 1 -> n request` по `initiator_user_id`
* `user_account 1 -> n request` по `operator_user_id`
* `account 1 -> n ledger_entry`
* `transaction_record 1 -> n ledger_entry`

