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

* `account_number ~ '^[0-9]{20}$'`
* `status in ('Active','Blocked','Closed')`
* `negative_balance_limit is null or negative_balance_limit >= 0`
* `balance >= 0 or (negative_balance_limit is not null and balance >= -negative_balance_limit)`
* `(status = 'Closed') = (closed_at is not null)`
* `status <> 'Closed' or balance = 0`
* `unique (user_id, currency_id, account_type_code)`

**Правила состояния:**

* `Blocked` запрещает новые операции и закрытие счёта;
* `Blocked` не скрывает счёт из списков и истории;
* разблокировка переводит счёт обратно в `Active`.

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
* `from_account_id is null or to_account_id is null or from_account_id <> to_account_id`
* `transaction_type <> 'Deposit' or (from_account_id is null and to_account_id is not null)`
* `transaction_type <> 'Withdraw' or (from_account_id is not null and to_account_id is null)`
* `transaction_type <> 'Transfer' or (from_account_id is not null and to_account_id is not null)`
* `transaction_type <> 'Compensation' or related_transaction_id is not null`
* `transaction_type = 'Compensation' or related_transaction_id is null`
* `related_transaction_id is null or related_transaction_id <> transaction_id`

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

**Ограничения:**

* `amount <> 0`

**Правила суммы:**

* отрицательная сумма означает списание со счёта;
* положительная сумма означает зачисление на счёт;
* сумма финансовой операции в `transaction_record.amount` остаётся положительной.

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

В API поле `request_id` этой таблицы представляется как `application_id`, чтобы не смешиваться со сквозным `request_id` HTTP-запроса.

**Ограничения:**

* `request_type in ('UserRegistration','AccountOpening','Deposit','Withdraw','Transfer')`
* `status in ('PendingApproval','Approved','Rejected')`
* `result_entity_type is null or result_entity_type in ('User','Account','Transaction')`
* `(result_entity_type is null) = (result_entity_id is null)`
* `(status = 'PendingApproval') = (decided_at is null)`
* `status <> 'PendingApproval' or (operator_user_id is null and reason_code is null and result_entity_type is null)`
* `status = 'PendingApproval' or (operator_user_id is not null and reason_code is not null)`
* `status <> 'Approved' or result_entity_type is not null`
* `status <> 'Rejected' or result_entity_type is null`

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
* `Transfer`: `from_account_id`, `to_account_number`, `amount`, `currency_id`

Во внешнем API заявка `UserRegistration` принимает `password`; при сохранении в `request.payload` пароль заменяется на `password_hash`.

### 2.8. `reason_code`

**Назначение:** единый справочник причин.

**Поля:**

* `reason_code varchar(...) pk`
* `name varchar(...) not null`
* `description varchar(...) not null`
* `scope varchar(...) not null`
* `status varchar(...) not null`

**Ограничения:**

* `scope in ('Request','Transaction','User','Both')`
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

**Ограничения:**

* `key in ('bank_name','registration_mode','account_opening_mode','internal_transfer_mode','cash_in_out_mode')`
* `value_type in ('string','mode')`
* `key = 'bank_name'` требует `value_type = 'string'` и непустое `value`
* `key = 'registration_mode'` требует `value_type = 'mode'` и `value in ('auto','manual')`
* `key = 'account_opening_mode'` требует `value_type = 'mode'` и `value in ('auto','manual')`
* `key = 'internal_transfer_mode'` требует `value_type = 'mode'` и `value in ('enabled','manual','disabled')`
* `key = 'cash_in_out_mode'` требует `value_type = 'mode'` и `value in ('manual','disabled')`

**Начальное значение:**

* `cash_in_out_mode = manual`

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

Поле `audit_log.request_id` хранит сквозной идентификатор HTTP-запроса, а не ссылку на `request.request_id`.

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
* `idempotency_scope varchar(...) not null`
* `endpoint varchar(...) not null`
* `idempotency_key uuid not null`
* `request_hash varchar(...) not null`
* `response_status integer not null`
* `response_body jsonb not null`
* `created_at timestamptz not null`

**Ограничения:**

* `idempotency_scope <> ''`
* `unique (idempotency_scope, endpoint, idempotency_key)`

**Правила области идемпотентности:**

* для аутентифицированного пользователя `idempotency_scope = 'user:' || user_id`;
* для неаутентифицированных маршрутов `POST /auth/register` и `POST /auth/login` используется `idempotency_scope = 'anonymous'`;
* область идемпотентности не является секретом и не заменяет проверку доступа.

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

## 4. Сверка схемы перед миграциями

Раздел фиксирует границу между ограничениями PostgreSQL и проверками серверной части. Цель сверки — подготовить проектную схему к начальным миграциям без переноса в БД правил, которые зависят от текущего сценария, роли пользователя, режима работы системы или состояния нескольких связанных записей.

### 4.1. Проверки уровня PostgreSQL

PostgreSQL должен удерживать статические ограничения, которые можно проверить по одной строке или через ключи и уникальность:

* первичные ключи всех таблиц;
* внешние ключи между `user_account`, `account`, `transaction_record`, `ledger_entry`, `request`, `currency`, `account_type`, `reason_code` и `refresh_session`;
* уникальность `user_account.email`, `user_account.username`, `user_account.phone_number`;
* уникальность `account.account_number` и формат 20 цифр;
* уникальность `account(user_id, currency_id, account_type_code)` без исключения закрытых счетов;
* допустимые статусы и типы через `check`;
* неотрицательность `account.negative_balance_limit`;
* нижнюю границу `account.balance`: баланс не меньше нуля, если лимит не задан, и не меньше `-negative_balance_limit`, если лимит задан;
* закрытый счёт имеет заполненный `closed_at` и `balance = 0`, а незакрытый счёт не имеет `closed_at`;
* положительную сумму `transaction_record.amount`;
* ненулевую сумму `ledger_entry.amount`, где знак отражает списание или зачисление;
* уникальность `idempotency_entry(idempotency_scope, endpoint, idempotency_key)`;
* уникальность `refresh_session.token_hash`;
* фиксированный набор ключей `system_setting` и допустимые значения режимов.

Эти ограничения не заменяют прикладные проверки, но защищают базу от явно невозможных состояний.

### 4.2. Проверки серверной части

Серверная часть должна проверять правила, которые требуют знания сценария, текущего пользователя, режима работы или нескольких строк:

* генерацию уникального `account_number` и повтор генерации при конфликте уникальности;
* активность `currency` и `account_type` при создании счёта или заявки;
* согласование `negative_balance_limit` с `account_type.allow_negative_balance`;
* запрет новых операций и закрытия для счёта в статусе `Blocked`;
* запрет новых операций для счёта в статусе `Closed`;
* закрытие только активного счёта при `balance = 0` с блокировкой строки счёта;
* проверку валюты операции против валют всех затронутых счетов;
* расчёт итогового баланса в одной транзакции с блокировкой строк счетов;
* правило отрицательного баланса: уход в минус допускается только для `Transfer`, только при разрешённом типе счёта и только в пределах лимита;
* запрет перевода на тот же счёт;
* создание согласованных проводок только для успешной финансовой операции;
* проверку `request.payload` по `request_type`;
* применение режимов `registration_mode`, `account_opening_mode`, `internal_transfer_mode`, `cash_in_out_mode`;
* проверку области применения `reason_code.scope`;
* проверку ролей и областей видимости из матрицы доступа;
* сохранение и повторное воспроизведение ответа по `Idempotency-Key`.

### 4.3. Начальные справочники и режимы

Начальные данные применяются после создания таблиц `currency`, `account_type`, `reason_code` и `system_setting`. Шаг начального наполнения должен быть воспроизводимым: повторный запуск не создаёт дубликаты и обновляет записи по естественным ключам `currency_code`, `account_type_code`, `reason_code` и `key`.

#### 4.3.1. Валюты

Минимальный набор валют первой версии:

| `currency_id` | `currency_code` | `name` | `precision` | `status` | Назначение |
| --- | --- | --- | --- | --- | --- |
| `d2d907b5-70f5-4d39-a3f3-01f42e8c68dd` | `RUB` | Российский рубль | `2` | `Active` | Базовая валюта для открытия счетов, переводов, пополнений и выводов в первой версии. |

Правила:

* все начальные валюты имеют уникальный трёхбуквенный `currency_code`, `precision between 2 and 10` и статус `Active`;
* первая рабочая версия не требует нескольких валют для запуска основных сценариев;
* добавление новых валют выполняется отдельным решением по справочникам, без изменения исторических операций.

#### 4.3.2. Типы счетов

Минимальный набор типов счетов первой версии:

| `account_type_code` | `name` | `allow_negative_balance` | `status` | Назначение |
| --- | --- | --- | --- | --- |
| `CURRENT` | Текущий счёт | `false` | `Active` | Обычный счёт без права уйти в минус. |
| `CREDIT` | Кредитный счёт | `true` | `Active` | Счёт, на котором допустим отрицательный баланс в пределах `negative_balance_limit`. |

Правила:

* все начальные типы счетов имеют уникальный `account_type_code`, статус `Active` и явно заданный `allow_negative_balance`;
* `negative_balance_limit` задаётся на конкретном счёте, а не в справочнике типов;
* серверная часть должна отклонять ненулевой `negative_balance_limit` для типа с `allow_negative_balance = false`.

#### 4.3.3. Причины решений

Минимальный набор причин решений первой версии:

| `reason_code` | `name` | `description` | `scope` | `status` | Назначение |
| --- | --- | --- | --- | --- | --- |
| `CLIENT_REQUEST` | Запрос клиента | Решение принято по обращению клиента. | `Request` | `Active` | Причина для заявок, созданных по инициативе клиента. |
| `APPROVED_BY_OPERATOR` | Одобрено оператором | Оператор одобрил заявку после проверки. | `Request` | `Active` | Причина успешного решения заявки. |
| `REJECTED_BY_OPERATOR` | Отклонено оператором | Оператор отклонил заявку после проверки. | `Request` | `Active` | Причина отказа по заявке. |
| `OPERATOR_CORRECTION` | Корректировка оператором | Оператор создаёт корректирующую компенсацию. | `Transaction` | `Active` | Причина операции `Compensation`. |
| `SECURITY_REVIEW` | Проверка безопасности | Статус пользователя изменён после проверки безопасности. | `User` | `Active` | Причина блокировки или разблокировки пользователя. |

Правила:

* начальные причины решений используют `scope in ('Request','Transaction','User','Both')` и статус `Active`;
* `Request` применяется к одобрению и отклонению заявок;
* `Transaction` применяется к компенсациям финансовых операций;
* `User` применяется к изменению статуса пользователя и фиксируется в аудите;
* `Both` зарезервирован для причин, которые одинаково применимы к заявкам и операциям.

#### 4.3.4. Режимы работы системы

Начальная таблица `system_setting` содержит ровно разрешённые ключи:

| `setting_id` | `key` | `value` | `value_type` | `description` |
| --- | --- | --- | --- | --- |
| `04b646cb-1f4d-4f95-b353-2f7fd826edfb` | `bank_name` | `VBank` | `string` | Отображаемое имя системы. |
| `75c62702-f2e1-47f8-bcf7-d6d7dbb3e9a0` | `registration_mode` | `auto` | `mode` | Регистрация пользователя создаёт `Client` без ручной заявки. |
| `a82a2774-f39c-4dd6-9ff3-53c79f400f2f` | `account_opening_mode` | `auto` | `mode` | Открытие счёта через `POST /accounts` создаёт счёт сразу. |
| `6be06937-c0ea-4936-aa8d-3f5ec21c4957` | `internal_transfer_mode` | `enabled` | `mode` | Внутренний перевод выполняется напрямую. |
| `ab3bb372-dfad-468a-9f17-81c7404f56e5` | `cash_in_out_mode` | `manual` | `mode` | Пополнение и вывод доступны только через заявку. |

Правила:

* `bank_name` хранится как непустая строка;
* режимы используют `value_type = 'mode'` и значения из допустимых наборов таблицы `system_setting`;
* `cash_in_out_mode` стартует как `manual`, потому что пополнение и вывод в первой версии проходят через заявку;
* стартовые значения `registration_mode = auto`, `account_opening_mode = auto` и `internal_transfer_mode = enabled` позволяют запустить базовый сценарий без заранее созданных пользователей и без секретов в репозитории.

Результат сверки: явных противоречий между проектной схемой, требованиями и начальными режимами не выявлено. Схема готова к применению начальных справочников после начальной миграции Alembic без создания каталога `migrations` в этой работе.

## 5. План начальной миграции Alembic

Начальная миграция должна создать схему VBank на пустой базе PostgreSQL в воспроизводимом порядке. В этой работе фиксируется план миграции; каталог `migrations` и файлы ревизий не создаются.

### 5.1. Общие правила миграций

* миграции выполняются через Alembic;
* миграции применяются только вперёд;
* уже применённая миграция не изменяется задним числом, исправления добавляются новой ревизией;
* откат миграции не является штатным способом исправления состояния базы;
* начальная миграция создаёт только схему, а состав начальных справочников и режимов берётся из раздела 4.3;
* имена ограничений и индексов должны быть стабильными: `pk_*`, `fk_*`, `uq_*`, `ck_*`, `ix_*`.

### 5.2. Порядок создания таблиц

Начальная миграция создаёт таблицы в порядке зависимостей:

1. `user_account` — базовая таблица пользователей без внешних ключей.
2. `currency` — справочник валют.
3. `account_type` — справочник типов счетов.
4. `reason_code` — справочник причин решений.
5. `system_setting` — режимы работы системы.
6. `account` — счета, после `user_account`, `currency` и `account_type`.
7. `transaction_record` — финансовые операции, после `account`, `currency`, `reason_code` и `user_account`.
8. `request` — заявки, после `user_account` и `reason_code`.
9. `ledger_entry` — проводки, после `account`, `currency` и `transaction_record`.
10. `refresh_session` — отзывные сессии обновления, после `user_account`.
11. `audit_log` — журнал аудита; `actor_id` не получает внешний ключ, потому что `actor_type` может быть `User`, `Operator`, `Admin` или `System`.
12. `idempotency_entry` — хранилище идемпотентности; `idempotency_scope` хранится без внешнего ключа, чтобы покрыть аутентифицированные и неаутентифицированные изменяющие запросы.

Самоссылка `transaction_record.related_transaction_id -> transaction_record.transaction_id` создаётся после создания таблицы `transaction_record` либо внутри `create_table`, если выбранный стиль Alembic явно поддерживает такое ограничение.

### 5.3. Ограничения первой миграции

Первая миграция должна создать:

* первичные ключи всех таблиц;
* внешние ключи, перечисленные в разделе 2;
* уникальные ограничения `user_account.email`, `user_account.username`, `user_account.phone_number`, `account.account_number`, `account(user_id, currency_id, account_type_code)`, `currency.currency_code`, `account_type.account_type_code`, `reason_code.reason_code`, `system_setting.key`, `refresh_session.token_hash`, `idempotency_entry(idempotency_scope, endpoint, idempotency_key)`;
* `check`-ограничения статусов, ролей, типов операций, типов заявок, областей `reason_code.scope`, режимов `system_setting`, денежных сумм, формата `account_number`, правил `closed_at` и нулевого баланса закрытого счёта;
* `not null` для обязательных полей;
* nullable-поля только там, где это указано в модели данных.

Для доменных правил из раздела 4.2 миграция создаёт только те ограничения, которые можно выразить статически. Проверки активности справочников, прав доступа, переходов состояния, блокировки строк и расчёта баланса остаются в серверной части.

### 5.4. Индексы первой миграции

После создания таблиц и ограничений миграция создаёт неуникальные индексы:

* `ix_user_account_role`
* `ix_user_account_status`
* `ix_account_user_id`
* `ix_account_status`
* `ix_transaction_record_initiator_user_id`
* `ix_transaction_record_from_account_id`
* `ix_transaction_record_to_account_id`
* `ix_transaction_record_created_at`
* `ix_transaction_record_related_transaction_id`
* `ix_ledger_entry_account_id_created_at`
* `ix_ledger_entry_transaction_id`
* `ix_request_initiator_user_id`
* `ix_request_operator_user_id`
* `ix_request_status_created_at`
* `ix_request_request_type`
* `ix_request_result_entity`
* `ix_audit_log_actor_id_created_at`
* `ix_audit_log_action_type_created_at`
* `ix_audit_log_request_id`
* `ix_idempotency_entry_created_at`
* `ix_refresh_session_user_id`
* `ix_refresh_session_expires_at`

Индексы, которые PostgreSQL создаёт автоматически для первичных ключей и уникальных ограничений, отдельно не дублируются.

### 5.5. Проверка начальной миграции

Готовая миграция должна проходить на пустой базе по цепочке:

1. применить все ревизии Alembic вперёд;
2. убедиться, что созданы все таблицы, внешние ключи, ограничения и индексы из разделов 2 и 5;
3. применить начальные справочники и режимы из раздела 4.3;
4. повторить проверку на новой пустой базе без ручных действий.

Правка уже применённой ревизии вместо новой миграции запрещена.

## 6. Сверка инвариантов и связей данных

Сверка фиксирует, какие правила удерживает схема PostgreSQL, а какие должна проверять серверная часть. Если правило зависит от роли, текущего режима, нескольких строк, расчёта баланса или внешнего маршрута, оно остаётся в серверной части и покрывается тестом.

### 6.1. Инварианты и место проверки

| Область | Инвариант | Уровень PostgreSQL | Уровень серверной части | Проверка при реализации |
| --- | --- | --- | --- | --- |
| `User` | `email`, `username`, `phone_number` уникальны; роль и статус входят в допустимые наборы. | `unique`, `check role`, `check status`. | Блокировка входа и новых действий для `Blocked`; проверка переходов `Active <-> Blocked`. | Дубли регистрации, вход заблокированного пользователя, смена статуса. |
| `Account` | Счёт уникален по `(user_id, currency_id, account_type_code)`, номер состоит из 20 цифр, закрытый счёт имеет `closed_at` и нулевой баланс. | `fk`, `unique`, `check account_number`, `check status`, `check balance`, `check closed_at`. | Активность валюты и типа счёта; запрет операций и закрытия для `Blocked` и `Closed`; согласование `negative_balance_limit` с `AccountType`. | Открытие дубля, закрытие с ненулевым балансом, операции по заблокированному и закрытому счёту. |
| `Transaction` | Сумма операции положительная; тип, статус и форма счётов соответствуют типу операции; компенсация ссылается на исходную операцию. | `fk`, `check transaction_type`, `check status`, `check amount`, `check` формы `from_account_id` и `to_account_id`, самоссылка `related_transaction_id`. | Совпадение валют, доступность счетов, достаточность средств, лимит отрицательного баланса, атомарный расчёт балансов и блокировка строк. | Успешный перевод, перевод на тот же счёт, нехватка средств, превышение лимита, компенсация неуспешной операции. |
| `LedgerEntry` | Проводка ссылается на счёт и операцию, сумма проводки не равна нулю и хранит знак движения. | `fk`, `check amount <> 0`, индексы по счёту и операции. | Создание проводок только для `Transaction.status = Success`; балансировка проводок и операции в одной транзакции. | Успешный перевод создаёт две проводки; отклонённая операция не создаёт проводок; сумма проводок меняет баланс ожидаемо. |
| `Request` | Тип и статус заявки допустимы; `PendingApproval` не имеет решения; `Rejected` не имеет результата; результат хранится парой `result_entity_type` и `result_entity_id`. | `fk`, `check request_type`, `check status`, `check` полей решения и результата. | Создание заявки только при разрешённом режиме, проверка `payload`, финальность `Approved` и `Rejected`, создание результата только при `Approved`. | Ручная регистрация, ручное открытие счёта, пополнение, вывод, ручной перевод, повторное решение заявки. |
| Справочники и настройки | Начальные справочники активны, настройки имеют разрешённые ключи и значения. | `unique`, `check status`, `check scope`, `check system_setting`. | Проверка активности справочных записей и области `reason_code.scope` в сценарии. | Неактивная валюта или тип счёта отклоняются; неподходящий `ReasonCode` возвращает `REASON_CODE_NOT_ALLOWED`. |
| Идемпотентность | Повтор одного ключа в одной области и на одном маршруте не создаёт новый эффект. | `unique (idempotency_scope, endpoint, idempotency_key)`. | Расчёт `request_hash`, возврат сохранённого ответа при полном совпадении и `IDEMPOTENCY_REPLAY_CONFLICT` при другом теле. | Повтор `POST` с тем же ключом и телом; повтор с тем же ключом и другим телом. |
| Аудит | Запись аудита содержит тип актора, контекст, результат и сквозной `request_id` HTTP-запроса. | `check actor_type`, индекс по `request_id`; внешний ключ на `actor_id` не задаётся из-за полиморфного актора. | Запись аудита для каждой значимой попытки и результата; корреляция с ответом API. | Успешные и отклонённые действия создают аудит с тем же `request_id`. |

### 6.2. Связи данных

Обязательные связи первой версии:

* `account.user_id -> user_account.user_id`;
* `account.currency_id -> currency.currency_id`;
* `account.account_type_code -> account_type.account_type_code`;
* `transaction_record.from_account_id -> account.account_id`;
* `transaction_record.to_account_id -> account.account_id`;
* `transaction_record.currency_id -> currency.currency_id`;
* `transaction_record.reason_code -> reason_code.reason_code`;
* `transaction_record.initiator_user_id -> user_account.user_id`;
* `transaction_record.related_transaction_id -> transaction_record.transaction_id`;
* `ledger_entry.account_id -> account.account_id`;
* `ledger_entry.currency_id -> currency.currency_id`;
* `ledger_entry.transaction_id -> transaction_record.transaction_id`;
* `request.initiator_user_id -> user_account.user_id`;
* `request.operator_user_id -> user_account.user_id`;
* `request.reason_code -> reason_code.reason_code`;
* `refresh_session.user_id -> user_account.user_id`.

Полиморфные связи проверяются серверной частью:

* `request.result_entity_type` и `request.result_entity_id` указывают на созданный `User`, `Account` или `Transaction` после одобрения заявки;
* `audit_log.actor_id` трактуется вместе с `actor_type`, поэтому не имеет одного внешнего ключа;
* `idempotency_entry.idempotency_scope` хранит область повтора для пользователя или анонимного маршрута и не ссылается на одну таблицу.

### 6.3. Проверяемость критериев приёмки

Критерии приёмки из технического задания покрываются следующими группами тестов:

* регистрация и вход: тесты режимов `registration_mode`, уникальности пользователя, входа по трём идентификаторам и блокировки `Blocked`;
* счета: тесты уникальности `(user_id, currency_id, account_type_code)`, формата номера, закрытия только при `balance = 0`, запрета действий для `Blocked` и `Closed`;
* переводы: тесты атомарного изменения двух балансов, двух проводок, запрета перевода на тот же счёт, нехватки средств и лимита отрицательного баланса;
* пополнение и вывод: тесты создания заявки, одобрения с операцией и проводкой, отклонения без финансового эффекта;
* идемпотентность и аудит: тесты повторного `Idempotency-Key`, конфликта тела запроса и записи аудита с `request_id`;
* справочники и настройки: тесты начальных данных из раздела 4.3, фильтрации справочников и изменения разрешённых настроек.

Результат сверки: явных противоречий между доменными инвариантами, схемой PostgreSQL и API-договором не осталось. Правила, которые нельзя надёжно выразить ограничением одной строки, явно оставлены серверной части и имеют проверяемые критерии.
