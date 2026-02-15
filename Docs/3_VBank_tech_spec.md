* 2026.02.15 20:44:10

# Техническое задание на разработку виртуального банка VBank

---

## 1. Цель и назначение приложения

### 1.1. Цель
Создать виртуальную банковскую систему VBank с минимальным банковским учётом, транзакционностью, аудитом и разграничением доступа по ролям.

### 1.2. Назначение
- Ведение счетов пользователей в нескольких валютах.
- Внутренние переводы между счетами.
- Операции пополнения/вывода через заявки с одобрением Оператора (Operator) согласно режимам системы.
- Регистрация пользователей и открытие счетов могут требовать одобрения Оператора (Operator) согласно режимам системы.
- История операций, история заявок и аудит действий.

---

## 2. Целевая аудитория

- Пользователи (Client): выполнение операций и управление своими счетами.
- Операторы (Operator): управление пользователями и обработка их заявок/операций.
- Администраторы (Admin): управление технической конфигурацией системы, справочниками и аудитом.

---

## 3. Роли пользователей (Role)

### 3.1. Пользователь (Client)
- Регистрируется и входит в систему.
- Управляет своими счетами (просмотр, открытие/закрытие — в рамках режимов).
- Создаёт операции/заявки в рамках режимов.
- Просматривает историю своих операций и заявок.

### 3.2. Оператор (Operator)
- Управляет пользователями (создание, блокировка/разблокировка).
- Обрабатывает заявки (одобрение/отклонение) с указанием причины (ReasonCode).
- Имеет доступ к персональным данным пользователей и полной истории операций пользователей.
- Создаёт компенсирующие операции (Compensation) в рамках полномочий.

### 3.3. Администратор (Admin)
- Управляет технической стороной системы:
    - справочниками (Currency, AccountType, ReasonCode);
    - настройками системы (SystemSetting);
    - аудитом (AuditLog);
    - техническими параметрами доступа/секретами через конфигурацию деплоя (вне UI).
- Назначение/изменение ролей Operator/Admin (если требуется) относится к Admin.

---

## 4. Состав функций (функциональные области)

1) Идентификация и доступ (Auth)
2) Пользователи и роли (UserManagement)
3) Счета (AccountManagement)
4) Операции (TransactionProcessing)
5) Заявки и решения (RequestWorkflow)
6) Справочники (Dictionaries)
7) Настройки (SystemSettings)
8) История и аудит (HistoryAndAudit)

---

## 5. Сценарии использования (UseCases)

### UC-01 Регистрация пользователя (UserRegistrationRequest / UserRegistration)
Зависит от НастройкиСистемы (SystemSetting) `registration_mode`:
- Auto: пользователь создаётся сразу.
- Manual: создаётся заявка; Оператор (Operator) одобряет; пользователь создаётся только при Approved.

### UC-02 Вход (Login)
Пользователь вводит идентификатор (Username/Email/PhoneNumber) и пароль, получает access/refresh.

### UC-03 Открытие счёта (AccountOpeningRequest / AccountOpening)
Зависит от `account_opening_mode`:
- Auto: счёт создаётся сразу.
- Manual: создаётся заявка; Оператор (Operator) одобряет; затем создаётся счёт.

### UC-04 Перевод (Transfer)
Зависит от `internal_transfer_mode`:
- Enabled: создаётся ФинансоваяОперация (Transaction) типа Transfer напрямую.
- Manual: создаётся Заявка (Request) типа Transfer; Оператор (Operator) одобряет; затем создаётся Transaction.Transfer.

Правило: уход в минус допускается только для Transfer и только для счёта с AllowNegativeBalance=true при наличии лимита на уровне счёта.

### UC-05 Пополнение (DepositRequest / Deposit)
Создаётся Request.Deposit; Оператор (Operator) одобряет; затем создаётся Transaction.Deposit и Проводки (LedgerEntry).

### UC-06 Вывод (WithdrawRequest / Withdraw)
Создаётся Request.Withdraw; Оператор (Operator) одобряет; затем создаётся Transaction.Withdraw и LedgerEntry.
Правило: Withdraw не может приводить к отрицательному балансу.

### UC-07 Компенсация (Compensation)
Оператор (Operator) создаёт Transaction.Compensation, которая логически компенсирует исходную операцию.

### UC-08 История операций и заявок (History)
Client видит только свои операции/заявки. Operator видит полную историю операций/заявок пользователей.

---

## 6. Функциональные требования (FR)

### 6.1. FR-Auth-01 Регистрация (UserRegistration)
- Входные атрибуты: Email (email), PhoneNumber (phone_number), Username (username), Password (password).
- Уникальность: email, phone_number, username.
- Режим Auto: создаётся Пользователь (User) со статусом Active.
- Режим Manual: создаётся Заявка (Request) типа UserRegistration, статус Created → PendingApproval; User создаётся только при Approved.

### 6.2. FR-Auth-02 Вход/обновление токенов
- Login: принимает `login` (строка; username/email/phone_number) и `password`.
- Возвращает access JWT и refresh JWT.
- Refresh: принимает refresh JWT и возвращает новую пару (access+refresh).
- Logout: уничтожает access JWT и refresh JWT.

### 6.3. FR-User-01 Управление пользователями (Operator)
- Оператор (Operator):
    - создаёт пользователей (включая создание через одобрение заявки при Manual);
    - блокирует/разблокирует пользователей;
    - просматривает список пользователей и карточку пользователя.
- Admin:
    - назначает/снимает роли Operator/Admin (при необходимости).

### 6.4. FR-Account-01 Счета (Account)
- Инвариант: один пользователь может иметь не более одного счёта одного типа в одной валюте.
- Открытие счёта:
    - валюта активна;
    - тип счёта существует;
    - номер счёта генерируется системой;
    - лимит отрицательного баланса задаётся на уровне счёта для типов с AllowNegativeBalance=true.
- Закрытие счёта:
    - допустимо только при balance = 0;
    - статус становится Closed;
    - физическое удаление запрещено.

### 6.5. FR-Tx-01 Общие правила операций (Transaction)
- Status: Success / Rejected. Cancelled отсутствует.
- Amount > 0.
- Валюта операции обязана совпадать с валютой участвующих счетов.
- При Rejected: LedgerEntry не создаются; причина фиксируется (reason_code).

### 6.6. FR-Tx-02 Перевод (Transfer)
- Вход: FromAccount (from_account_id), ToAccountNumber (to_account_number), Amount (amount).
- Проверки:
    - from_account принадлежит инициатору (Client) либо инициатор — Operator (при служебных действиях);
    - to_account существует и активен;
    - валюта совпадает;
    - перевод на тот же счёт запрещён;
    - если allow_negative_balance=false: balance_after >= 0;
    - если allow_negative_balance=true:
        - уход в минус разрешён только для Transfer;
        - лимит обязателен на уровне счёта (negative_balance_limit); правило `balance_after >= -negative_balance_limit`.
- Исполнение:
    - атомарная транзакция БД;
    - блокировка счетов `SELECT ... FOR UPDATE` (from_account и to_account);
    - запись Transaction + 2 LedgerEntry (списание/зачисление);
    - обновление балансов счетов.

### 6.7. FR-Tx-03 Пополнение/вывод (Deposit/Withdraw)
- Deposit: увеличивает баланс, создаёт LedgerEntry (+).
- Withdraw: уменьшает баланс, создаёт LedgerEntry (−).
- Withdraw не допускает отрицательный итоговый баланс независимо от allow_negative_balance.

### 6.8. FR-Account-02 Лимит отрицательного баланса (NegativeBalanceLimit)
- Лимит отрицательного баланса задаётся на уровне Счёта (Account) атрибутом negative_balance_limit.
- Для счетов с allow_negative_balance=true:
    - лимит обязателен для возможности Transfer в минус;
    - при отсутствии лимита операция, ведущая к отрицательному балансу, должна быть Rejected (ReasonCode: NEGATIVE_LIMIT_NOT_SET).

### 6.9. FR-Request-01 Заявки (Request)
- Типы: UserRegistration, AccountOpening, Deposit, Withdraw, Transfer.
- Статусы: Created, PendingApproval, Approved, Rejected.
- Created — технический статус до постановки в очередь; после успешной валидации переводится в PendingApproval.
- Одобрение/отклонение выполняет Operator с указанием ReasonCode.
- При Approved:
    - создаётся соответствующая Transaction (если применимо),
    - Request.result_transaction_id заполняется.

### 6.10. FR-Dict-01 Справочники (Admin)
- Валюта (Currency): CurrencyId, CurrencyCode, Name, Precision, Status.
- ТипСчёта (AccountType): AccountTypeCode, ProductTypeCode, Name, AllowNegativeBalance.
- КодПричины (ReasonCode): единый справочник причин/отказов для Request и Transaction.
- Удаление записей справочников запрещено; допускается Disabled/архивация статусом.

### 6.11. FR-Settings-01 Настройки (SystemSetting)
- Хранятся как ключ-значение.
- Набор допустимых ключей фиксирован; запись неизвестных ключей запрещена.
- Минимальные ключи:
    - BankName
    - RegistrationMode: Auto/Manual
    - InternalTransferMode: Enabled/Disabled/Manual
    - CashInOutMode: Manual/Disabled
    - AccountOpeningMode: Auto/Manual

### 6.12. FR-Audit-01 Аудит (AuditLog)
- Фиксируются все попытки и результаты:
    - вход/выход/refresh;
    - регистрация/одобрение регистрации;
    - открытие/закрытие счетов;
    - создание/одобрение/отклонение заявок;
    - создание операций и их исход;
    - изменения справочников и настроек.
- Записи audit неизменяемы: UPDATE/DELETE запрещены на уровне БД-ролей.

---

## 7. Требования к данным (DataRequirements)

### 7.1. Общие правила хранения
- Идентификаторы сущностей: UUID.
- Денежные суммы: PostgreSQL `numeric(38,10)`; входные значения валидируются по Currency.precision (без округления).
- Все временные метки: UTC.

### 7.2. Сущности (Entities) и ключевые атрибуты
Формат имён:
- Сущность: CamelCase
- Атрибут: snake_case

#### Пользователь (User)
- Идентификатор (user_id)
- Email (email)
- Логин (username)
- Номер телефона (phone_number)
- Хэш пароля (password_hash)
- Роль (role)
- Статус (status)
- Дата регистрации (registered_at)

#### Счёт (Account)
- Идентификатор (account_id)
- Номер счёта (account_number)
- Идентификатор пользователя (user_id)
- Идентификатор валюты (currency_id)
- Код типа счёта (account_type_code)
- Баланс (balance)
- Лимит отрицательного баланса (negative_balance_limit) — nullable
- Статус (status)
- Дата создания (created_at)
- Дата закрытия (closed_at) — nullable

Уникальность:
- (user_id, currency_id, account_type_code)

#### ТипСчёта (AccountType)
- Код типа счёта (account_type_code)
- Код типа продукта (product_type_code)
- Наименование (name)
- Разрешён отрицательный баланс (allow_negative_balance)

#### Валюта (Currency)
- Идентификатор (currency_id)
- Код валюты (currency_code)
- Наименование (name)
- Точность (precision)
- Статус (status)

#### ФинансоваяОперация (Transaction)
- Идентификатор (transaction_id)
- Тип операции (transaction_type)
- Идентификатор счёта-источника (from_account_id) — nullable
- Идентификатор счёта-получателя (to_account_id) — nullable
- Номер счёта получателя (to_account_number) — nullable (для входа Transfer)
- Сумма (amount)
- Идентификатор валюты (currency_id)
- Статус (status)
- Код причины (reason_code) — nullable
- Идентификатор инициатора (initiator_user_id)
- Идентификатор исходной операции (related_transaction_id) — nullable (для Compensation)
- Дата создания (created_at)
- Дата завершения (completed_at) — nullable

#### Проводка (LedgerEntry)
- Идентификатор (ledger_entry_id)
- Идентификатор счёта (account_id)
- Сумма (amount) — signed
- Идентификатор валюты (currency_id)
- Идентификатор операции (transaction_id)
- Дата создания (created_at)

#### Заявка (Request)
- Идентификатор (request_id)
- Тип (request_type)
- Статус (status)
- Идентификатор инициатора (initiator_user_id)
- Идентификатор счёта (account_id) — nullable
- Сумма (amount) — nullable
- Идентификатор валюты (currency_id) — nullable
- Код причины (reason_code) — nullable
- Идентификатор оператора (operator_user_id) — nullable
- Идентификатор результирующей операции (result_transaction_id) — nullable
- Дата создания (created_at)
- Дата постановки в очередь (queued_at) — nullable
- Дата решения (decided_at) — nullable

#### КодПричины (ReasonCode)
- Код (reason_code)
- Наименование (name)
- Описание (description)
- Область применения (scope) — Request/Transaction/Both
- Статус (status)

#### НастройкаСистемы (SystemSetting)
- Идентификатор (setting_id)
- Ключ (key)
- Значение (value)
- Тип значения (value_type)
- Описание (description)
- Дата обновления (updated_at)

#### Аудит (AuditLog)
- Идентификатор (audit_id)
- Тип субъекта (actor_type)
- Идентификатор субъекта (actor_id)
- Действие (action_type)
- Контекст (context)
- Время (timestamp)

### 7.3. Идемпотентность (Idempotency)
- Все изменяющие запросы обязаны принимать заголовок `Idempotency-Key` (UUID).
- В хранилище идемпотентности фиксируются:
    - actor_id, endpoint, idempotency_key, request_hash, response_body, response_status, created_at.
- Повторный запрос с тем же ключом возвращает исходный ответ без повторного выполнения.

### 7.4. Номер счёта (AccountNumber)
- Формат: 20 цифр.
- Генерация системой по структуре:
    - 1–3: категория клиента (100/200)
    - 4–6: числовой код валюты
    - 7–9: product_type_code
    - 10–20: уникальная последовательность клиента/счёта
- Проверка: уникальность account_number в пределах системы.
- Маппинг currency_code → numeric_code фиксируется в конфигурации/коде; для RUB/USD/EUR должен быть задан.

---

## 8. Требования к интерфейсу (JavaFX)

### 8.1. Общие требования UX
- Валидация ввода до отправки (формат, обязательность).
- Единый формат ошибок API: `{code, message, details, request_id}`.
- Списки (очереди/история) с пагинацией.

### 8.2. Экраны Client
- Вход/Регистрация
- Счета: список, детали, открыть/закрыть
- Перевод: форма + подтверждение (или создание заявки при Manual)
- Заявки: создать (Deposit/Withdraw/Transfer при Manual), список, детали
- История операций: фильтры + детали

### 8.3. Экраны Operator
- Пользователи: список/карточка/создание/блокировка/разблокировка
- Очередь заявок (PendingApproval)
- Карточка заявки: approve/reject + выбор ReasonCode
- История операций/заявок пользователей (просмотр)

### 8.4. Экраны Admin
- Справочники: Currency, AccountType, ReasonCode
- Настройки: SystemSetting (только разрешённые ключи)
- Аудит: просмотр

---

## 9. Нефункциональные требования (NFR)

### 9.1. Производительность
- Transfer: 95-й перцентиль времени ответа < 1 сек при локальной БД.
- Списки: постраничная выдача; ответ < 1 сек для страницы до 50 записей.

### 9.2. Надёжность и консистентность
- Денежные операции атомарны: либо полностью применены, либо не применены.
- Транзакционный контроль: блокировка строк счетов `SELECT ... FOR UPDATE`.
- Для Success Transfer обязательны 2 проводки (списание и зачисление).

### 9.3. Безопасность
- TLS.
- Пароли: безопасное хэширование (bcrypt/argon2id).
- Refresh-токены хранятся в БД и могут быть отозваны.
- RBAC на каждом запросе.
- Rate limit на Login/Refresh.
- Секреты (ключи JWT, доступ к БД) не хранятся в коде.

### 9.4. Наблюдаемость
- `request_id` в каждом ответе и логах.
- Структурированные логи.
- Корреляция действий AuditLog с запросами.

---

## 10. Допущения и ограничения

### 10.1. Допущения
- Маппинг числовых кодов валют задан для RUB/USD/EUR и расширяем.
- Operator имеет право видеть персональные данные и полную историю операций пользователей.
- Withdraw не допускает уход в минус.

### 10.2. Ограничения
- Нет интеграций с внешними банками/платёжными шлюзами.
- Нет конвертации валют.
- Нет KYC/AML.
- Нет отмены операций (Cancel запрещён).

---

## 11. Требования к API (высокий уровень)

### 11.1. Общие правила
- Base path: `/api/v1`
- Ошибка: JSON `{code, message, details, request_id}`
- Все изменяющие операции требуют `Idempotency-Key`.

### 11.2. Основные эндпоинты
Auth:
- POST `/auth/register`
- POST `/auth/login`
- POST `/auth/refresh`
- POST `/auth/logout`

Users (Operator / Admin по полномочиям):
- GET `/users` (Operator)
- GET `/users/{user_id}` (Operator)
- POST `/users` (Operator)
- PATCH `/users/{user_id}/status` (Operator)
- PATCH `/users/{user_id}/role` (Admin)

Accounts:
- GET `/accounts` (Client)
- POST `/accounts` (Client; AccountOpeningMode)
- POST `/accounts/{account_id}/close` (Client)

Transactions:
- POST `/transactions/transfer` (Client; InternalTransferMode=Enabled)
- POST `/transactions/compensation` (Operator)

Requests:
- POST `/requests` (Client)
- GET `/requests` (Client/Operator)
- POST `/requests/{request_id}/approve` (Operator)
- POST `/requests/{request_id}/reject` (Operator)

Dictionaries (Admin):
- GET `/currencies` (All)
- POST `/currencies` (Admin)
- PATCH `/currencies/{currency_id}` (Admin)

- GET `/account-types` (All)
- POST `/account-types` (Admin)
- PATCH `/account-types/{account_type_code}` (Admin)

- GET `/reason-codes` (All)
- POST `/reason-codes` (Admin)
- PATCH `/reason-codes/{reason_code}` (Admin)

Settings (Admin):
- GET `/settings` (Admin)
- PATCH `/settings/{key}` (Admin)

Audit (Admin):
- GET `/audit` (Admin)

---

## 12. Критерии приёмки (AcceptanceCriteria)

1) Регистрация:
- Auto: пользователь создаётся Active и может войти.
- Manual: без Approved пользователь не создаётся и войти не может.

2) Аутентификация:
- Login по username/email/phone_number работает.
- Refresh выдаёт новые токены.
- Logout отзывает refresh (повторный refresh отклоняется).

3) Идемпотентность:
- Повтор любого POST/PUT/PATCH/DELETE с тем же Idempotency-Key возвращает идентичный результат и не создаёт дубликаты.

4) Пользователи:
- Operator создаёт пользователя, блокирует/разблокирует пользователя.
- Заблокированный пользователь не может выполнять операции и входить (если так установлено политикой блокировки).

5) Счета:
- Создание счёта соблюдает уникальность (user_id, currency_id, account_type_code).
- Закрытие счёта возможно только при balance=0; после Closed операции запрещены.

6) Переводы:
- Enabled: Transfer выполняется атомарно, создаёт Transaction.Success и 2 LedgerEntry.
- Недостаток средств при allow_negative_balance=false → Rejected с ReasonCode.
- allow_negative_balance=true и задан negative_balance_limit:
  - Transfer допускает уход в минус до лимита.
- Withdraw не допускает уход в минус.

7) Заявки:
- Deposit/Withdraw/Transfer(Manual)/Registration(Manual)/AccountOpening(Manual) проходят через Request + решение Operator.
- Approve создаёт соответствующую Transaction и заполняет result_transaction_id.
- Reject не создаёт LedgerEntry и фиксирует ReasonCode.

8) Справочники и настройки:
- Currency соответствует набору полей: id/code/name/precision/status.
- SystemSetting запрещает неизвестные ключи.
- Режимы реально влияют на доступность действий (Registration/Transfer/AccountOpening/CashInOut).

9) Аудит:
- Любая попытка действия (успех/отказ) фиксируется в AuditLog.
- Записи AuditLog неизменяемы (проверка прав БД/приложения).

---
