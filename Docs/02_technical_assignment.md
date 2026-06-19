# VBank — техническое задание

## 1. Цель разработки

Разработать внутреннюю виртуальную банковскую систему VBank с набором функций:

* управление пользователями и доступом;
* открытие и ведение счетов;
* выполнение внутренних финансовых операций;
* ручная обработка заявок;
* управление справочниками и режимами работы системы;
* аудит значимых действий.

Целевая форма системы:

* серверная часть на Python с HTTP API;
* отдельное веб-приложение для пользователей трёх ролей;
* консольный клиент как первый внешний интерфейс для разработки, проверки и приёмки сценариев;
* PostgreSQL как основное хранилище данных.

## 2. Пользователи системы

* `Client` — работает только со своими объектами;
* `Operator` — обрабатывает заявки и выполняет служебные действия;
* `Admin` — управляет справочниками, режимами работы системы и аудитом.

У пользователя в каждый момент времени одна активная роль. Отдельная система разрешений в первой версии не вводится.

## 3. Функциональные требования

### 3.1. Аутентификация и сессии

Система должна:

* регистрировать пользователя напрямую в режиме `auto` или создавать заявку в режиме `manual`;
* выполнять вход по `username`, `email` или `phone_number`;
* выдавать короткоживущий `access token`;
* поддерживать отзывной `refresh token`;
* поддерживать обновление и отзыв сессии;
* возвращать текущего пользователя и его роль для внешних клиентов.

### 3.2. Пользователи

Система должна:

* хранить пользователя с одной активной ролью доступа;
* позволять оператору просматривать пользователей, блокировать и разблокировать их;
* позволять администратору изменять роль пользователя;
* запрещать заблокированному пользователю вход и новые действия.

### 3.3. Счета

Система должна:

* открывать счёт в активной валюте и существующем типе счёта;
* использовать `POST /accounts` как основной маршрут открытия счёта;
* при `account_opening_mode = auto` создавать счёт сразу и возвращать созданный счёт;
* при `account_opening_mode = manual` создавать заявку типа `AccountOpening` и возвращать созданную заявку;
* генерировать уникальный 20-значный `account_number`;
* обеспечивать уникальность сочетания `(user_id, currency_id, account_type_code)`;
* показывать заблокированный счёт в списках и истории;
* запрещать новые операции и закрытие счёта в статусе `Blocked`;
* закрывать счёт только при `balance = 0`;
* запрещать новые операции по счёту в статусе `Closed`.

### 3.4. Финансовые операции

Система должна:

* поддерживать операции `Transfer`, `Deposit`, `Withdraw`, `Compensation`;
* выполнять операцию целиком или не выполнять её вовсе;
* использовать хранимый баланс счёта как рабочее состояние;
* создавать проводки только для успешной операции;
* хранить сумму проводки со знаком: списание отрицательным значением, зачисление положительным значением;
* запрещать отмену проведённой операции;
* использовать `Compensation` для исправления ранее проведённой операции.

### 3.5. Переводы

Система должна:

* принимать во внешнем запросе перевода `from_account_id`, `to_account_number`, `amount`, `currency_id`;
* определять счёт-получатель по `to_account_number` на серверной стороне;
* выполнять перевод напрямую при `internal_transfer_mode = enabled`;
* создавать заявку на перевод при `internal_transfer_mode = manual`;
* запрещать перевод при `internal_transfer_mode = disabled`;
* запрещать перевод на тот же счёт;
* проверять право инициатора распоряжаться счётом-источником, если инициатором не является оператор;
* создавать две проводки при успешном переводе.

### 3.6. Пополнение и вывод

Система должна:

* обрабатывать пополнение и вывод только через заявку;
* использовать начальное значение `cash_in_out_mode = manual`;
* отклонять пополнение и вывод без создания заявки при `cash_in_out_mode = disabled`;
* создавать финансовую операцию только после одобрения заявки;
* создавать одну проводку для `Deposit` и одну проводку для `Withdraw`;
* запрещать `Withdraw`, если итоговый баланс становится отрицательным.

### 3.7. Заявки

Система должна:

* поддерживать типы заявок `UserRegistration`, `AccountOpening`, `Deposit`, `Withdraw`, `Transfer`;
* использовать `POST /requests` как общий маршрут явного создания заявки;
* не заменять маршрутом `POST /requests` предметные команды, для которых есть отдельный маршрут API;
* использовать статусы `PendingApproval`, `Approved`, `Rejected`;
* позволять оператору одобрять или отклонять заявку с указанием `ReasonCode`;
* создавать результат только после `Approved`;
* не создавать результат после `Rejected`.

### 3.8. Справочники и режимы работы

Система должна:

* хранить справочники `Currency`, `AccountType`, `ReasonCode`;
* запрещать физическое удаление справочных записей;
* хранить только фиксированный набор ключей `SystemSetting`;
* применять режимы работы системы к пользовательским сценариям без перезапуска приложения.

### 3.9. Аудит и история

Система должна:

* показывать клиенту только его собственные счета, операции и заявки;
* показывать оператору историю пользователей и очередь заявок;
* показывать администратору журнал аудита;
* фиксировать в аудите каждую значимую попытку и результат.

## 4. Требования к API

### 4.1. Общие правила

* базовый путь API: `/api/v1`;
* API является единым договором для веб-приложения и консольного клиента;
* консольный клиент не должен обращаться напрямую к прикладному слою серверной части;
* формат ошибки: `{code, message, details, request_id}`;
* `request_id` в ответах и ошибках является сквозным идентификатором HTTP-запроса, а не идентификатором заявки;
* каждый ответ должен содержать или позволять сопоставить `request_id`;
* заявка во внешнем API представляется полем `application_id`;
* все изменяющие запросы должны принимать заголовок `Idempotency-Key`;
* доступ к операциям должен управляться по роли пользователя.

### 4.2. Аутентификация внешних клиентов

* `access token` используется как `Authorization: Bearer ...`;
* `refresh token` должен быть отзывным и храниться в `refresh_session`;
* для веб-приложения `refresh token` СЛЕДУЕТ передавать в cookie с признаками `HttpOnly`, `Secure`, `SameSite`;
* для веб-приложения `access token` СЛЕДУЕТ хранить только в памяти приложения;
* для консольного клиента `refresh token` СЛЕДУЕТ хранить вне репозитория в пользовательском хранилище;
* секреты и токены ЗАПРЕЩЕНО хранить в репозитории.

### 4.3. Обязательные операции API

* `POST /auth/register`
* `POST /auth/login`
* `POST /auth/refresh`
* `POST /auth/logout`
* `GET /auth/me`
* `GET /accounts`
* `POST /accounts`
* `GET /accounts/{account_id}`
* `POST /accounts/{account_id}/close`
* `GET /transactions`
* `POST /transfers`
* `POST /transactions/compensations`
* `POST /requests`
* `GET /requests`
* `GET /requests/{application_id}`
* `POST /requests/{application_id}/approve`
* `POST /requests/{application_id}/reject`
* `GET /users`
* `GET /users/{user_id}`
* `PATCH /users/{user_id}/status`
* `PATCH /users/{user_id}/role`
* `GET /currencies`
* `GET /account-types`
* `GET /reason-codes`
* `GET /settings`
* `PATCH /settings/{key}`
* `GET /audit`

### 4.4. Общие правила маршрутов `/api/v1`

Все маршруты ниже указываются относительно базового пути `/api/v1`.

Общие правила:

* все изменяющие запросы `POST` и `PATCH` принимают заголовок `Idempotency-Key`;
* все маршруты, кроме регистрации, входа, обновления и выхода из сессии, требуют `Authorization: Bearer ...`;
* успешный ответ содержит данные результата и позволяет сопоставить ответ со сквозным `request_id` HTTP-запроса;
* ошибки возвращаются в формате `{code, message, details, request_id}`;
* в таблицах ниже указаны классы основных ошибок, а не окончательный справочник кодов ошибок;
* полные форматы JSON-полей уточняются отдельно, но состав входных данных должен соответствовать доменной модели и модели данных.

### 4.5. Аутентификация и сессии

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `POST /auth/register` | Зарегистрировать пользователя напрямую в режиме `auto` или создать заявку `UserRegistration` в режиме `manual`. | Тело: `email`, `username`, `phone_number`, `password`; заголовок `Idempotency-Key`. | В режиме `auto` — созданный пользователь; в режиме `manual` — созданная заявка с `application_id` и статусом `PendingApproval`. | Ошибка проверки данных, конфликт уникальности, регистрация запрещена режимом, повторный ключ идемпотентности с другим телом. | Требования 3.1, 3.7; модель `auth`, `User`, `Request`. |
| `POST /auth/login` | Выполнить вход по `username`, `email` или `phone_number`. | Тело: `login`, `password`; заголовок `Idempotency-Key`. | `access token`, данные текущего пользователя, сведения о refresh-сессии или cookie с `refresh token`. | Неверные учётные данные, пользователь заблокирован, пользователь из ручной регистрации ещё не одобрен, повторный ключ идемпотентности с другим телом. | Требования 3.1, 4.2; модель `auth`, `User`, `refresh_session`. |
| `POST /auth/refresh` | Обновить короткоживущий `access token` по отзывному `refresh token`. | `refresh token` из cookie или тела запроса; заголовок `Idempotency-Key`. | Новый `access token` и актуальное состояние refresh-сессии. | Refresh-сессия не найдена, истекла или отозвана; пользователь заблокирован; повторный ключ идемпотентности с другим телом. | Требования 3.1, 4.2; модель `auth`, `refresh_session`. |
| `POST /auth/logout` | Отозвать текущую refresh-сессию. | `refresh token` из cookie или тела запроса; заголовок `Idempotency-Key`; при наличии — `Authorization`. | Признак успешного выхода и отзыва refresh-сессии. | Refresh-сессия не найдена или уже отозвана, ошибка доступа, повторный ключ идемпотентности с другим телом. | Требования 3.1, 4.2; модель `auth`, `refresh_session`. |
| `GET /auth/me` | Получить текущего пользователя и его роль. | `Authorization`. | Текущий пользователь: `user_id`, публичные идентификаторы, `role`, `status`. | Нет или недействителен `access token`, пользователь заблокирован или не найден. | Требования 3.1, 3.2; модель `auth`, `User`. |

### 4.6. Счета и операции

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `GET /accounts` | Получить список видимых счетов. | `Authorization`; параметры фильтрации и пагинации. | Страница счетов, включая заблокированные и закрытые счета, если они входят в область видимости роли. | Ошибка доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.3, 3.9; модель `Account`, правила доступа. |
| `POST /accounts` | Открыть счёт или создать заявку `AccountOpening` при ручном режиме. | Тело: `currency_id`, `account_type_code`, `negative_balance_limit`; заголовок `Idempotency-Key`; `Authorization`. | В режиме `auto` — созданный счёт; в режиме `manual` — заявка с `application_id` и статусом `PendingApproval`. | Валюта или тип счёта неактивны, дубликат `(user_id, currency_id, account_type_code)`, недопустимый лимит отрицательного баланса, пользователь заблокирован, повторный ключ идемпотентности с другим телом. | Требования 3.3, 3.7; модель `Account`, `Request`, `Currency`, `AccountType`. |
| `GET /accounts/{account_id}` | Получить карточку счёта. | `account_id`; `Authorization`. | Счёт с балансом, статусом, валютой, типом, номером счёта и датами. | Счёт не найден, нет доступа, пользователь заблокирован. | Требования 3.3, 3.9; модель `Account`. |
| `POST /accounts/{account_id}/close` | Закрыть активный счёт. | `account_id`; заголовок `Idempotency-Key`; `Authorization`. | Счёт в статусе `Closed` с заполненным `closed_at`. | Счёт не найден, нет доступа, счёт заблокирован или уже закрыт, баланс не равен нулю, повторный ключ идемпотентности с другим телом. | Требования 3.3; модель `Account.status`. |
| `GET /transactions` | Получить историю видимых финансовых операций. | `Authorization`; фильтры по счёту, типу, статусу, периоду и пагинации. | Страница операций `Transfer`, `Deposit`, `Withdraw`, `Compensation` с основными ссылками на счета и заявки. | Ошибка доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.4, 3.9; модель `Transaction`, `LedgerEntry`. |
| `POST /transfers` | Выполнить внутренний перевод или создать заявку `Transfer` при ручном режиме. | Тело: `from_account_id`, `to_account_number`, `amount`, `currency_id`; заголовок `Idempotency-Key`; `Authorization`. | При `internal_transfer_mode = enabled` — успешная операция `Transfer`; при `manual` — заявка с `application_id`; при `disabled` успешный ответ не возвращается. | Счёт не найден, нет доступа к счёту-источнику, перевод на тот же счёт, несовпадение валют, недостаточно средств или нарушен лимит отрицательного баланса, счёт заблокирован или закрыт, режим `disabled`, повторный ключ идемпотентности с другим телом. | Требования 3.4, 3.5, 3.7; модель `Transaction`, `Account`, `Request`. |
| `POST /transactions/compensations` | Создать компенсацию ранее проведённой операции. | Тело: `related_transaction_id`, `reason_code`, параметры компенсации; заголовок `Idempotency-Key`; `Authorization`. | Успешная операция `Compensation`, связанная с исходной операцией. | Исходная операция не найдена или неуспешна, компенсация недопустима по состоянию счетов, причина неактивна или не подходит по области, нет доступа, повторный ключ идемпотентности с другим телом. | Требования 3.4; модель `Transaction`, `Compensation`, `ReasonCode`. |

### 4.7. Заявки

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `POST /requests` | Явно создать заявку для сценария, у которого нет отдельной предметной команды, или для пополнения и вывода. | Тело: `request_type`, `payload`; заголовок `Idempotency-Key`; `Authorization`. | Созданная заявка с `application_id`, типом, статусом `PendingApproval` и полезной нагрузкой. | Тип заявки недопустим, `payload` не соответствует типу, сценарий должен идти через отдельный маршрут, режим запрещает создание заявки, пользователь заблокирован, повторный ключ идемпотентности с другим телом. | Требования 3.6, 3.7; модель `Request`, `payload`. |
| `GET /requests` | Получить список видимых заявок. | `Authorization`; фильтры по типу, статусу, инициатору, периоду и пагинации. | Страница заявок с внешним идентификатором `application_id`. | Ошибка доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.7, 3.9; модель `Request`, правила доступа. |
| `GET /requests/{application_id}` | Получить карточку заявки. | `application_id`; `Authorization`. | Заявка с типом, статусом, инициатором, оператором, полезной нагрузкой, причиной и результатом. | Заявка не найдена, нет доступа, пользователь заблокирован. | Требования 3.7; модель `Request`. |
| `POST /requests/{application_id}/approve` | Одобрить ожидающую заявку и создать результат предметной области. | `application_id`; тело с `reason_code`; заголовок `Idempotency-Key`; `Authorization`. | Заявка в статусе `Approved` и ссылка на созданный результат: пользователя, счёт или операцию. | Заявка не найдена, нет доступа, заявка уже решена, причина неактивна или не подходит, результат нельзя создать из-за предметных правил, повторный ключ идемпотентности с другим телом. | Требования 3.6, 3.7; модель `Request.status`, `ReasonCode`, соответствующий результат. |
| `POST /requests/{application_id}/reject` | Отклонить ожидающую заявку без создания предметного результата. | `application_id`; тело с `reason_code`; заголовок `Idempotency-Key`; `Authorization`. | Заявка в статусе `Rejected` с причиной решения. | Заявка не найдена, нет доступа, заявка уже решена, причина неактивна или не подходит, повторный ключ идемпотентности с другим телом. | Требования 3.7; модель `Request.status`, `ReasonCode`. |

### 4.8. Пользователи

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `GET /users` | Получить список пользователей в области видимости роли. | `Authorization`; фильтры по роли, статусу и пагинации. | Страница пользователей с ролью и статусом. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.2, 3.9; модель `User`, правила доступа. |
| `GET /users/{user_id}` | Получить карточку пользователя. | `user_id`; `Authorization`. | Пользователь с публичными идентификаторами, ролью, статусом и датой регистрации. | Пользователь не найден, нет доступа, пользователь заблокирован. | Требования 3.2; модель `User`. |
| `PATCH /users/{user_id}/status` | Изменить статус пользователя между `Active` и `Blocked`. | `user_id`; тело: `status`, причина изменения; заголовок `Idempotency-Key`; `Authorization`. | Пользователь с обновлённым статусом. | Пользователь не найден, нет доступа, недопустимый переход статуса, повторный ключ идемпотентности с другим телом. | Требования 3.2; модель `User.status`. |
| `PATCH /users/{user_id}/role` | Изменить активную роль пользователя. | `user_id`; тело: `role`; заголовок `Idempotency-Key`; `Authorization`. | Пользователь с обновлённой ролью. | Пользователь не найден, нет доступа, недопустимая роль, пользователь заблокирован, повторный ключ идемпотентности с другим телом. | Требования 2, 3.2; модель `User.role`. |

### 4.9. Справочники и режимы работы

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `GET /currencies` | Получить справочник валют. | `Authorization`; фильтры по статусу и пагинации. | Список или страница валют `Currency`. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.8; модель `Currency`. |
| `GET /account-types` | Получить справочник типов счетов. | `Authorization`; фильтры по статусу и пагинации. | Список или страница типов счетов `AccountType`. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.8; модель `AccountType`. |
| `GET /reason-codes` | Получить справочник причин решений. | `Authorization`; фильтры по области `scope`, статусу и пагинации. | Список или страница причин `ReasonCode`. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.7, 3.8; модель `ReasonCode`. |
| `GET /settings` | Получить режимы работы системы. | `Authorization`; фильтры по ключу и пагинации. | Список настроек `SystemSetting`, включая `registration_mode`, `account_opening_mode`, `internal_transfer_mode`, `cash_in_out_mode`. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.8; модель `SystemSetting`. |
| `PATCH /settings/{key}` | Изменить значение разрешённой настройки системы. | `key`; тело: `value`; заголовок `Idempotency-Key`; `Authorization`. | Настройка `SystemSetting` с обновлённым значением и временем изменения. | Ключ не разрешён, значение не соответствует типу или допустимому набору, нет доступа, повторный ключ идемпотентности с другим телом. | Требования 3.8; модель `SystemSetting`. |

### 4.10. Аудит

| Маршрут | Назначение | Входные данные | Успешный ответ | Основные ошибки | Связь |
| --- | --- | --- | --- | --- | --- |
| `GET /audit` | Получить журнал значимых действий и результатов. | `Authorization`; фильтры по актору, действию, результату, периоду, `request_id` HTTP-запроса и пагинации. | Страница записей `AuditLog` с контекстом действия и сквозным `request_id`. | Нет доступа, ошибка фильтрации, пользователь заблокирован. | Требования 3.9, 6.3; модель `AuditLog`. |

### 4.11. Форматы запросов и ответов

Раздел задаёт JSON-форматы для обязательных маршрутов `/api/v1`. Ошибки остаются в формате `{code, message, details, request_id}` и детализируются отдельно.

#### 4.11.1. Общие правила JSON

* имена JSON-полей передаются в `snake_case`;
* идентификаторы сущностей передаются строками `uuid`;
* `application_id` используется только для внешнего идентификатора заявки и соответствует внутреннему `request.request_id`;
* `request_id` используется только для сквозного идентификатора HTTP-запроса;
* `account_number` передаётся строкой из 20 цифр;
* денежные значения передаются строкой с десятичной записью, совместимой с `numeric(38,10)`;
* `transaction.amount` всегда положительный, а `ledger_entry.amount` хранит знак движения средств;
* временные метки передаются строками RFC 3339 в UTC, например `2026-06-19T12:30:00Z`;
* статусные поля используют значения из доменной модели без локализации;
* известные пустые значения возвращаются как `null`, неизвестные или неприменимые поля не добавляются в ответ;
* пароли, хэши паролей, хэши токенов и секреты не возвращаются во внешних ответах;
* изменяющие запросы `POST` и `PATCH` принимают заголовок `Idempotency-Key` в формате `uuid`;
* успешный ответ одного объекта возвращается как:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {}
}
```

* успешный ответ списка возвращается как:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": [],
  "page": {
    "limit": 50,
    "offset": 0,
    "total": 0
  }
}
```

#### 4.11.2. Общие объекты ответа

`User`:

```json
{
  "user_id": "8cf15db6-6733-4e51-9a4c-20c580c5b1e9",
  "email": "client@example.test",
  "username": "client1",
  "phone_number": "+79990000001",
  "role": "Client",
  "status": "Active",
  "registered_at": "2026-06-19T12:30:00Z"
}
```

`Currency`:

```json
{
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd",
  "currency_code": "RUB",
  "name": "Российский рубль",
  "precision": 2,
  "status": "Active"
}
```

`AccountType`:

```json
{
  "account_type_code": "CURRENT",
  "name": "Текущий счёт",
  "allow_negative_balance": false,
  "status": "Active"
}
```

`ReasonCode`:

```json
{
  "reason_code": "CLIENT_REQUEST",
  "name": "Запрос клиента",
  "description": "Решение принято по обращению клиента",
  "scope": "Request",
  "status": "Active"
}
```

`SystemSetting`:

```json
{
  "setting_id": "ab3bb372-dfad-468a-9f17-81c7404f56e5",
  "key": "cash_in_out_mode",
  "value": "manual",
  "value_type": "enum",
  "description": "Режим пополнения и вывода",
  "updated_at": "2026-06-19T12:30:00Z"
}
```

`Account`:

```json
{
  "account_id": "3c0bd759-2b38-4794-9c07-1b3c38d8bb7d",
  "account_number": "40702810000000000001",
  "user_id": "8cf15db6-6733-4e51-9a4c-20c580c5b1e9",
  "currency": {
    "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd",
    "currency_code": "RUB",
    "precision": 2
  },
  "account_type": {
    "account_type_code": "CURRENT",
    "name": "Текущий счёт"
  },
  "balance": "1000.0000000000",
  "negative_balance_limit": null,
  "status": "Active",
  "created_at": "2026-06-19T12:30:00Z",
  "closed_at": null
}
```

`LedgerEntry`:

```json
{
  "ledger_entry_id": "7a890d1a-fb58-45c0-99df-c75c3f25b5dd",
  "account_id": "3c0bd759-2b38-4794-9c07-1b3c38d8bb7d",
  "amount": "-100.0000000000",
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd",
  "transaction_id": "2dc75cc1-797c-4e55-8997-dbd3d105157e",
  "created_at": "2026-06-19T12:30:00Z"
}
```

`Transaction`:

```json
{
  "transaction_id": "2dc75cc1-797c-4e55-8997-dbd3d105157e",
  "transaction_type": "Transfer",
  "from_account_id": "3c0bd759-2b38-4794-9c07-1b3c38d8bb7d",
  "to_account_id": "705812a2-9fdb-4ab8-bf3e-82efaec6e590",
  "amount": "100.0000000000",
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd",
  "status": "Success",
  "reason_code": null,
  "initiator_user_id": "8cf15db6-6733-4e51-9a4c-20c580c5b1e9",
  "related_transaction_id": null,
  "application_id": null,
  "ledger_entries": [],
  "created_at": "2026-06-19T12:30:00Z",
  "completed_at": "2026-06-19T12:30:01Z"
}
```

`Application`:

```json
{
  "application_id": "2a7b4a11-2d39-45a1-b885-8b3ce062ce4d",
  "request_type": "Transfer",
  "status": "PendingApproval",
  "initiator_user_id": "8cf15db6-6733-4e51-9a4c-20c580c5b1e9",
  "operator_user_id": null,
  "payload": {},
  "reason_code": null,
  "result": null,
  "created_at": "2026-06-19T12:30:00Z",
  "decided_at": null
}
```

`Application.result` после одобрения содержит тип и идентификатор результата:

```json
{
  "entity_type": "Transaction",
  "entity_id": "2dc75cc1-797c-4e55-8997-dbd3d105157e"
}
```

`AuditLog`:

```json
{
  "audit_id": "79a2b67d-161e-49aa-8856-6e9dd669c19a",
  "actor_type": "User",
  "actor_id": "8cf15db6-6733-4e51-9a4c-20c580c5b1e9",
  "action_type": "TransferCreated",
  "result": "Success",
  "context": {},
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "created_at": "2026-06-19T12:30:00Z"
}
```

#### 4.11.3. Аутентификация и сессии

`POST /auth/register` принимает:

```json
{
  "email": "client@example.test",
  "username": "client1",
  "phone_number": "+79990000001",
  "password": "plain-text-password"
}
```

При `registration_mode = auto` ответ содержит созданного пользователя:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "result_type": "User",
    "user": {},
    "application": null
  }
}
```

При `registration_mode = manual` ответ содержит заявку:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "result_type": "Application",
    "user": null,
    "application": {}
  }
}
```

`POST /auth/login` принимает:

```json
{
  "login": "client1",
  "password": "plain-text-password"
}
```

Успешный ответ входа и обновления сессии:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "access_token": "jwt",
    "token_type": "Bearer",
    "access_token_expires_at": "2026-06-19T12:45:00Z",
    "refresh_token": null,
    "refresh_session": {
      "refresh_session_id": "60a5a5e2-fae6-4a36-85eb-b177a67eb3dd",
      "issued_at": "2026-06-19T12:30:00Z",
      "expires_at": "2026-07-19T12:30:00Z",
      "revoked_at": null
    },
    "user": {}
  }
}
```

Если refresh-сессия передаётся через cookie, `refresh_token` в теле ответа равен `null`; для консольного клиента поле содержит значение токена.

`POST /auth/refresh` и `POST /auth/logout` принимают `refresh_token` в cookie или в теле:

```json
{
  "refresh_token": "refresh-token-for-cli"
}
```

`POST /auth/logout` возвращает:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "success": true,
    "refresh_session_id": "60a5a5e2-fae6-4a36-85eb-b177a67eb3dd",
    "revoked_at": "2026-06-19T12:35:00Z"
  }
}
```

`GET /auth/me` возвращает объект `User`.

#### 4.11.4. Счета и операции

`GET /accounts` принимает параметры строки запроса `status`, `currency_id`, `account_type_code`, `limit`, `offset` и возвращает страницу объектов `Account`.

`POST /accounts` принимает:

```json
{
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd",
  "account_type_code": "CURRENT",
  "negative_balance_limit": null
}
```

При `account_opening_mode = auto` ответ содержит счёт, при `manual` — заявку:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "result_type": "Account",
    "account": {},
    "application": null
  }
}
```

В ручном режиме `result_type` принимает значение `Application`, поле `account` равно `null`, а поле `application` содержит созданную заявку.

`GET /accounts/{account_id}` возвращает объект `Account`.

`POST /accounts/{account_id}/close` принимает пустое тело или `{}` и возвращает объект `Account` со статусом `Closed`.

`GET /transactions` принимает параметры строки запроса `account_id`, `transaction_type`, `status`, `created_from`, `created_to`, `limit`, `offset` и возвращает страницу объектов `Transaction`.

`POST /transfers` принимает:

```json
{
  "from_account_id": "3c0bd759-2b38-4794-9c07-1b3c38d8bb7d",
  "to_account_number": "40702810000000000002",
  "amount": "100.0000000000",
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd"
}
```

При `internal_transfer_mode = enabled` ответ содержит операцию, при `manual` — заявку:

```json
{
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f",
  "data": {
    "result_type": "Transaction",
    "transaction": {},
    "application": null
  }
}
```

В ручном режиме `result_type` принимает значение `Application`, поле `transaction` равно `null`, а поле `application` содержит созданную заявку.

`POST /transactions/compensations` принимает:

```json
{
  "related_transaction_id": "2dc75cc1-797c-4e55-8997-dbd3d105157e",
  "reason_code": "OPERATOR_CORRECTION",
  "from_account_id": "705812a2-9fdb-4ab8-bf3e-82efaec6e590",
  "to_account_id": "3c0bd759-2b38-4794-9c07-1b3c38d8bb7d",
  "amount": "100.0000000000",
  "currency_id": "d2d907b5-70f5-4d39-a3f3-01f42e8c68dd"
}
```

Ответ компенсации содержит объект `Transaction` с `transaction_type = Compensation`.

#### 4.11.5. Заявки

`POST /requests` принимает:

```json
{
  "request_type": "Deposit",
  "payload": {}
}
```

`payload` зависит от `request_type`:

| `request_type` | Формат `payload` во внешнем API |
| --- | --- |
| `UserRegistration` | `email`, `username`, `phone_number`, `password` |
| `AccountOpening` | `currency_id`, `account_type_code`, `negative_balance_limit` |
| `Deposit` | `account_id`, `amount`, `currency_id` |
| `Withdraw` | `account_id`, `amount`, `currency_id` |
| `Transfer` | `from_account_id`, `to_account_number`, `amount`, `currency_id` |

Во внутреннем хранении пароль из `UserRegistration.payload.password` заменяется на `password_hash`.

`GET /requests` принимает параметры строки запроса `request_type`, `status`, `initiator_user_id`, `created_from`, `created_to`, `limit`, `offset` и возвращает страницу объектов `Application`.

`GET /requests/{application_id}` возвращает объект `Application`.

`POST /requests/{application_id}/approve` принимает:

```json
{
  "reason_code": "APPROVED_BY_OPERATOR"
}
```

Ответ содержит объект `Application` со статусом `Approved` и заполненным `result`.

`POST /requests/{application_id}/reject` принимает:

```json
{
  "reason_code": "REJECTED_BY_OPERATOR"
}
```

Ответ содержит объект `Application` со статусом `Rejected`, заполненным `reason_code` и пустым `result`.

#### 4.11.6. Пользователи

`GET /users` принимает параметры строки запроса `role`, `status`, `limit`, `offset` и возвращает страницу объектов `User`.

`GET /users/{user_id}` возвращает объект `User`.

`PATCH /users/{user_id}/status` принимает:

```json
{
  "status": "Blocked",
  "reason_code": "SECURITY_REVIEW"
}
```

Ответ содержит обновлённый объект `User`.

`PATCH /users/{user_id}/role` принимает:

```json
{
  "role": "Operator"
}
```

Ответ содержит обновлённый объект `User`.

#### 4.11.7. Справочники, настройки и аудит

`GET /currencies` принимает параметры строки запроса `status`, `limit`, `offset` и возвращает страницу объектов `Currency`.

`GET /account-types` принимает параметры строки запроса `status`, `limit`, `offset` и возвращает страницу объектов `AccountType`.

`GET /reason-codes` принимает параметры строки запроса `scope`, `status`, `limit`, `offset` и возвращает страницу объектов `ReasonCode`.

`GET /settings` принимает параметры строки запроса `key`, `limit`, `offset` и возвращает страницу объектов `SystemSetting`.

`PATCH /settings/{key}` принимает:

```json
{
  "value": "enabled"
}
```

Ответ содержит обновлённый объект `SystemSetting`.

`GET /audit` принимает параметры строки запроса `actor_id`, `action_type`, `result`, `created_from`, `created_to`, `request_id`, `limit`, `offset` и возвращает страницу объектов `AuditLog`.

### 4.12. Единый формат ошибок и коды ошибок

Раздел задаёт обязательный формат ошибок для всех маршрутов `/api/v1`. Консольный клиент и веб-приложение должны уметь обрабатывать ошибку по стабильному `code`, показывать пользователю безопасное `message` и сохранять `request_id` для диагностики.

#### 4.12.1. Тело ошибки

Ошибка возвращается как JSON-объект:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Запрос содержит недопустимые поля",
  "details": {
    "category": "validation",
    "field_errors": [
      {
        "field": "amount",
        "code": "must_be_positive",
        "message": "Сумма должна быть больше нуля"
      }
    ]
  },
  "request_id": "0d68e8b8-4e32-40b2-9346-9b7e8f5d8b4f"
}
```

Правила:

* верхний уровень ошибки всегда содержит только обязательные поля `code`, `message`, `details`, `request_id`;
* `code` — стабильный машинный код в `UPPER_SNAKE_CASE`; клиенты не должны разбирать текст `message` для выбора поведения;
* `message` — короткое русскоязычное описание, безопасное для показа пользователю;
* `details` — объект; если деталей нет, возвращается `{}`;
* `details` не содержит пароли, токены, хэши, секреты и внутренние трассировки;
* `request_id` — сквозной идентификатор HTTP-запроса; он создаётся до проверки аутентификации и возвращается во всех ошибках;
* в ошибке не используются поля успешного ответа `data` и `page`.

#### 4.12.2. Категории ошибок

| Категория `details.category` | Назначение | Основные HTTP-статусы |
| --- | --- | --- |
| `validation` | Неверная структура запроса, параметры фильтрации, формат идентификатора, тело заявки или ключ идемпотентности. | `400`, `422` |
| `access` | Ошибка аутентификации, сессии, роли, области видимости или состояние пользователя, запрещающее действие. | `401`, `403` |
| `object_state` | Объект не найден, уже находится в финальном состоянии или не допускает действие из-за текущего статуса. | `404`, `409` |
| `business_rule` | Нарушено предметное правило VBank: деньги, режимы работы, справочники, заявки, компенсации. | `409`, `422` |

#### 4.12.3. Справочник кодов ошибок

| Код | Категория | HTTP | Когда используется |
| --- | --- | --- | --- |
| `VALIDATION_ERROR` | `validation` | `422` | Тело запроса не соответствует формату, поле отсутствует, имеет неверный тип или недопустимое значение. |
| `FILTER_INVALID` | `validation` | `400` | Параметры фильтрации, периода, пагинации или сортировки недопустимы. |
| `IDEMPOTENCY_KEY_REQUIRED` | `validation` | `400` | Изменяющий запрос `POST` или `PATCH` отправлен без `Idempotency-Key`. |
| `IDEMPOTENCY_KEY_INVALID` | `validation` | `400` | `Idempotency-Key` не является `uuid`. |
| `IDEMPOTENCY_REPLAY_CONFLICT` | `object_state` | `409` | Повторный запрос использует тот же `Idempotency-Key`, но другое тело или другой маршрут. |
| `REQUEST_TYPE_NOT_ALLOWED` | `validation` | `422` | `request_type` неизвестен или не поддерживается в `/requests`. |
| `PAYLOAD_TYPE_MISMATCH` | `validation` | `422` | `payload` заявки не соответствует выбранному `request_type`. |
| `SETTING_VALUE_INVALID` | `validation` | `422` | Значение настройки не соответствует типу или допустимому набору. |
| `AUTHENTICATION_REQUIRED` | `access` | `401` | Маршрут требует `Authorization`, но токен не передан. |
| `TOKEN_INVALID` | `access` | `401` | `access token` отсутствует, истёк, повреждён или не прошёл проверку. |
| `INVALID_CREDENTIALS` | `access` | `401` | Логин, почта, телефон или пароль неверны. |
| `REFRESH_SESSION_INVALID` | `access` | `401` | Refresh-сессия не найдена, истекла или отозвана. |
| `ACCESS_DENIED` | `access` | `403` | Роль или область видимости пользователя не позволяет выполнить действие. |
| `USER_BLOCKED` | `access` | `403` | Пользователь заблокирован и не может входить или инициировать новые действия. |
| `USER_PENDING_APPROVAL` | `object_state` | `409` | Пользователь из ручной регистрации ещё не одобрен и не может войти. |
| `OBJECT_NOT_FOUND` | `object_state` | `404` | Пользователь, счёт, операция, заявка, справочник или настройка не найдены либо не видны текущей роли. |
| `ACCOUNT_BLOCKED` | `object_state` | `409` | Счёт заблокирован и не принимает новые операции или закрытие. |
| `ACCOUNT_CLOSED` | `object_state` | `409` | Счёт закрыт и не принимает новые операции. |
| `APPLICATION_ALREADY_DECIDED` | `object_state` | `409` | Заявка уже находится в `Approved` или `Rejected`. |
| `TRANSACTION_NOT_SUCCESSFUL` | `object_state` | `409` | Исходная операция не существует как успешный бизнес-факт для компенсации. |
| `USER_STATUS_TRANSITION_INVALID` | `object_state` | `409` | Переход статуса пользователя не входит в разрешённые переходы. |
| `UNIQUE_CONFLICT` | `business_rule` | `409` | Нарушена уникальность почты, имени пользователя, телефона, номера счёта или другой уникальной пары. |
| `ACCOUNT_ALREADY_EXISTS` | `business_rule` | `409` | У пользователя уже есть счёт того же типа в той же валюте. |
| `MODE_DISABLED` | `business_rule` | `409` | Сценарий запрещён текущим режимом работы системы. |
| `SEPARATE_ROUTE_REQUIRED` | `business_rule` | `409` | Заявка пытается заменить предметную команду, для которой есть отдельный маршрут API. |
| `DICTIONARY_ENTRY_INACTIVE` | `business_rule` | `409` | Валюта, тип счёта или причина решения отключены. |
| `REASON_CODE_NOT_ALLOWED` | `business_rule` | `422` | `reason_code` не существует, отключён или не подходит по области применения. |
| `ACCOUNT_BALANCE_NOT_ZERO` | `business_rule` | `409` | Счёт нельзя закрыть, потому что баланс не равен нулю. |
| `NEGATIVE_BALANCE_NOT_ALLOWED` | `business_rule` | `422` | Тип счёта не разрешает отрицательный баланс. |
| `NEGATIVE_BALANCE_LIMIT_EXCEEDED` | `business_rule` | `422` | Операция нарушает лимит отрицательного баланса. |
| `INSUFFICIENT_FUNDS` | `business_rule` | `422` | Операция списания или перевода не может быть выполнена из-за недостатка средств. |
| `SAME_ACCOUNT_TRANSFER` | `business_rule` | `422` | Перевод направлен на тот же счёт. |
| `CURRENCY_MISMATCH` | `business_rule` | `422` | Валюта операции не совпадает с валютой затронутого счёта или счетов. |
| `COMPENSATION_NOT_ALLOWED` | `business_rule` | `409` | Компенсацию нельзя создать для указанной операции или состояния счетов. |
| `APPLICATION_RESULT_NOT_ALLOWED` | `business_rule` | `409` | Одобрение заявки не может создать результат из-за предметных правил. |

#### 4.12.4. Состав `details`

Для `validation`:

```json
{
  "category": "validation",
  "field_errors": [
    {
      "field": "payload.amount",
      "code": "must_be_positive",
      "message": "Сумма должна быть больше нуля"
    }
  ]
}
```

Для `access`:

```json
{
  "category": "access",
  "required_role": "Operator",
  "actor_role": "Client"
}
```

Для `object_state`:

```json
{
  "category": "object_state",
  "entity_type": "Application",
  "entity_id": "2a7b4a11-2d39-45a1-b885-8b3ce062ce4d",
  "current_status": "Approved",
  "expected_status": "PendingApproval"
}
```

Для `business_rule`:

```json
{
  "category": "business_rule",
  "rule": "transfer_requires_different_accounts",
  "related_entity_type": "Account",
  "reason_code": null
}
```

`ReasonCode` не заменяет код ошибки API. Если оператор отклоняет заявку, это успешный ответ со статусом заявки `Rejected` и заполненным `reason_code`. Если переданный `reason_code` нельзя использовать, API возвращает `REASON_CODE_NOT_ALLOWED`.

#### 4.12.5. Ошибки по ключевым сценариям

| Сценарий | Основные коды ошибок |
| --- | --- |
| Любой изменяющий запрос `POST` или `PATCH` | `IDEMPOTENCY_KEY_REQUIRED`, `IDEMPOTENCY_KEY_INVALID`, `IDEMPOTENCY_REPLAY_CONFLICT`, `VALIDATION_ERROR` |
| Регистрация | `VALIDATION_ERROR`, `UNIQUE_CONFLICT`, `MODE_DISABLED`, `IDEMPOTENCY_REPLAY_CONFLICT` |
| Вход, обновление и выход из сессии | `INVALID_CREDENTIALS`, `USER_BLOCKED`, `USER_PENDING_APPROVAL`, `REFRESH_SESSION_INVALID`, `TOKEN_INVALID` |
| Получение текущего пользователя | `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID`, `USER_BLOCKED`, `OBJECT_NOT_FOUND` |
| Список и карточка счёта | `AUTHENTICATION_REQUIRED`, `ACCESS_DENIED`, `FILTER_INVALID`, `OBJECT_NOT_FOUND`, `USER_BLOCKED` |
| Открытие счёта | `VALIDATION_ERROR`, `DICTIONARY_ENTRY_INACTIVE`, `ACCOUNT_ALREADY_EXISTS`, `NEGATIVE_BALANCE_NOT_ALLOWED`, `USER_BLOCKED`, `MODE_DISABLED` |
| Закрытие счёта | `OBJECT_NOT_FOUND`, `ACCESS_DENIED`, `ACCOUNT_BLOCKED`, `ACCOUNT_CLOSED`, `ACCOUNT_BALANCE_NOT_ZERO`, `USER_BLOCKED` |
| История операций | `AUTHENTICATION_REQUIRED`, `ACCESS_DENIED`, `FILTER_INVALID`, `USER_BLOCKED` |
| Внутренний перевод | `OBJECT_NOT_FOUND`, `ACCESS_DENIED`, `USER_BLOCKED`, `SAME_ACCOUNT_TRANSFER`, `CURRENCY_MISMATCH`, `INSUFFICIENT_FUNDS`, `NEGATIVE_BALANCE_LIMIT_EXCEEDED`, `ACCOUNT_BLOCKED`, `ACCOUNT_CLOSED`, `MODE_DISABLED` |
| Компенсация операции | `OBJECT_NOT_FOUND`, `TRANSACTION_NOT_SUCCESSFUL`, `COMPENSATION_NOT_ALLOWED`, `REASON_CODE_NOT_ALLOWED`, `ACCESS_DENIED`, `USER_BLOCKED` |
| Создание заявки | `REQUEST_TYPE_NOT_ALLOWED`, `PAYLOAD_TYPE_MISMATCH`, `SEPARATE_ROUTE_REQUIRED`, `MODE_DISABLED`, `USER_BLOCKED` |
| Просмотр заявок | `AUTHENTICATION_REQUIRED`, `ACCESS_DENIED`, `FILTER_INVALID`, `OBJECT_NOT_FOUND`, `USER_BLOCKED` |
| Одобрение или отклонение заявки | `OBJECT_NOT_FOUND`, `ACCESS_DENIED`, `USER_BLOCKED`, `APPLICATION_ALREADY_DECIDED`, `REASON_CODE_NOT_ALLOWED`, `APPLICATION_RESULT_NOT_ALLOWED` |
| Управление пользователями | `OBJECT_NOT_FOUND`, `ACCESS_DENIED`, `VALIDATION_ERROR`, `USER_STATUS_TRANSITION_INVALID`, `USER_BLOCKED` |
| Справочники, настройки и аудит | `AUTHENTICATION_REQUIRED`, `ACCESS_DENIED`, `FILTER_INVALID`, `OBJECT_NOT_FOUND`, `SETTING_VALUE_INVALID`, `USER_BLOCKED` |

### 4.13. Матрица доступа `Client`, `Operator`, `Admin`

Раздел задаёт правила доступа для обязательных маршрутов `/api/v1`. Проверка выполняется серверной частью после аутентификации и до выполнения предметного действия.

Общие правила:

* в первой версии доступ определяется только активной ролью пользователя: `Client`, `Operator`, `Admin`;
* отдельная система разрешений, прав на отдельные поля и пользовательских политик не вводится;
* `Client` работает только со своими счетами, операциями и заявками;
* `Operator` работает с пользователями, заявками, служебной историей, компенсациями и действиями обработки;
* `Admin` работает с режимами работы системы, справочными данными в пределах обязательного API и аудитом;
* если роль не имеет права на маршрут, возвращается `ACCESS_DENIED`;
* если объект существует, но не входит в область видимости роли, маршрут с идентификатором возвращает `OBJECT_NOT_FOUND`;
* если пользователь-исполнитель имеет статус `Blocked`, вход, обновление сессии, `GET /auth/me` и все маршруты с `Authorization` возвращают `USER_BLOCKED`, кроме `POST /auth/logout`, который может отозвать refresh-сессию без выполнения предметного действия.

#### 4.13.1. Области видимости ролей

| Роль | Область чтения | Область изменения |
| --- | --- | --- |
| `Client` | Собственный профиль через `GET /auth/me`, свои счета, свои операции, свои заявки, справочники и текущие режимы работы, необходимые для клиентских сценариев. | Регистрация без роли, вход и выход из своей сессии, открытие и закрытие своих счетов, перевод со своего счёта-источника, создание собственных заявок для сценариев без прямой предметной команды. |
| `Operator` | Пользователи, счета, операции и заявки в служебной области обработки, а также справочники и режимы работы, необходимые для принятия решений. | Одобрение и отклонение заявок, блокировка и разблокировка пользователей, служебные переводы, компенсации операций. |
| `Admin` | Пользователи для управления ролями, справочники, режимы работы системы, аудит. | Изменение активной роли пользователя и значений разрешённых настроек системы. |

#### 4.13.2. Чтение данных

| Маршрут | `Client` | `Operator` | `Admin` |
| --- | --- | --- | --- |
| `GET /auth/me` | Текущий пользователь. | Текущий пользователь. | Текущий пользователь. |
| `GET /accounts` | Только свои счета, включая `Blocked` и `Closed`. | Счета пользователей в служебной области обработки. | Нет доступа. |
| `GET /accounts/{account_id}` | Только свой счёт. | Счёт пользователя в служебной области обработки. | Нет доступа. |
| `GET /transactions` | Операции по своим счетам и своим заявкам. | Операции пользователей в служебной области обработки. | Нет доступа. |
| `GET /requests` | Только свои заявки. | Очередь и история заявок пользователей. | Нет доступа. |
| `GET /requests/{application_id}` | Только своя заявка. | Любая заявка из очереди или истории обработки. | Нет доступа. |
| `GET /users` | Нет доступа; собственные данные доступны через `GET /auth/me`. | Список пользователей для обслуживания и управления статусом. | Список пользователей для управления ролями. |
| `GET /users/{user_id}` | Нет доступа; собственные данные доступны через `GET /auth/me`. | Карточка пользователя для обслуживания и управления статусом. | Карточка пользователя для управления ролями. |
| `GET /currencies` | Чтение справочника для клиентских сценариев. | Чтение справочника для обработки заявок и операций. | Чтение справочника. |
| `GET /account-types` | Чтение справочника для открытия счёта. | Чтение справочника для обработки заявок. | Чтение справочника. |
| `GET /reason-codes` | Чтение причин, видимых в собственных заявках и операциях. | Чтение причин для решений по заявкам и компенсациям. | Чтение справочника причин. |
| `GET /settings` | Чтение текущих режимов, влияющих на клиентские действия. | Чтение текущих режимов для обработки заявок и операций. | Чтение всех разрешённых настроек. |
| `GET /audit` | Нет доступа. | Нет доступа. | Чтение журнала аудита. |

#### 4.13.3. Изменение данных и командные маршруты

| Маршрут | Кто может выполнять | Правило доступа |
| --- | --- | --- |
| `POST /auth/register` | Неаутентифицированный пользователь. | Создаёт пользователя с ролью `Client` при `registration_mode = auto` или заявку `UserRegistration` при `manual`. |
| `POST /auth/login` | Неаутентифицированный пользователь. | Вход запрещён, если найденный пользователь имеет статус `Blocked` или ещё не одобрен после ручной регистрации. |
| `POST /auth/refresh` | Владелец действующей refresh-сессии. | Новый `access token` выдаётся только для пользователя со статусом `Active`. |
| `POST /auth/logout` | Владелец refresh-сессии. | Отзывает refresh-сессию; допускается как безопасное завершение сессии без предметного действия. |
| `POST /accounts` | `Client`. | Открывает счёт для текущего клиента или создаёт его заявку `AccountOpening`; `Operator` и `Admin` не открывают счета этим маршрутом. |
| `POST /accounts/{account_id}/close` | `Client`. | Закрывает только собственный активный счёт при `balance = 0`; `Blocked` и `Closed` не закрываются. |
| `POST /transfers` | `Client`, `Operator`. | `Client` переводит только со своего счёта-источника; `Operator` может выполнить служебный перевод по правилам режима `internal_transfer_mode`; `Admin` не выполняет переводы. |
| `POST /transactions/compensations` | `Operator`. | Создаёт компенсацию успешной операции с допустимым `ReasonCode`; `Client` и `Admin` не создают компенсации. |
| `POST /requests` | `Client`. | Создаёт собственную заявку только для сценария, разрешённого режимом работы и не заменяющего отдельный предметный маршрут. |
| `POST /requests/{application_id}/approve` | `Operator`. | Одобряет только заявку в статусе `PendingApproval` и создаёт результат предметной области. |
| `POST /requests/{application_id}/reject` | `Operator`. | Отклоняет только заявку в статусе `PendingApproval` с допустимым `ReasonCode`. |
| `PATCH /users/{user_id}/status` | `Operator`. | Меняет статус пользователя между `Active` и `Blocked`; `Client` и `Admin` не меняют статус этим маршрутом. |
| `PATCH /users/{user_id}/role` | `Admin`. | Меняет активную роль пользователя на одно из значений `Client`, `Operator`, `Admin`. |
| `PATCH /settings/{key}` | `Admin`. | Меняет только разрешённые ключи `SystemSetting`: `bank_name`, `registration_mode`, `account_opening_mode`, `internal_transfer_mode`, `cash_in_out_mode`. |

В обязательном API первой версии нет маршрутов изменения `Currency`, `AccountType` и `ReasonCode`. Эти справочники читаются через `/currencies`, `/account-types` и `/reason-codes`; их начальное наполнение и дальнейшее управление уточняются отдельно от F2-05.

#### 4.13.4. Поведение заблокированного пользователя

Пользователь со статусом `Blocked` не может входить, обновлять `access token`, получать текущий профиль и выполнять маршруты, требующие `Authorization`.

Правила отказа:

* `POST /auth/login` и `POST /auth/refresh` возвращают `USER_BLOCKED`;
* `GET /auth/me` и маршруты с `Authorization` возвращают `USER_BLOCKED`, если исполнитель уже заблокирован;
* `POST /auth/logout` может отозвать refresh-сессию заблокированного пользователя, потому что это не создаёт нового предметного результата;
* блокировка пользователя не скрывает уже созданные счета, операции, заявки и записи аудита от ролей, которые имеют право их читать;
* пользователь со статусом `Blocked` может быть разблокирован оператором через `PATCH /users/{user_id}/status`.

## 5. Требования к интерфейсам

### 5.1. Консольный клиент

Консольный клиент является первым внешним интерфейсом VBank.

Он должен:

* работать только через `/api/v1`;
* поддерживать вход под ролями `Client`, `Operator`, `Admin`;
* позволять пройти основные сценарии без веб-приложения;
* использовать те же правила ошибок, ролей и сессий, что и веб-приложение.

### 5.2. Веб-приложение

Веб-приложение является отдельным клиентским приложением.

Оно должно:

* работать только через `/api/v1`;
* иметь отдельные разделы для ролей `Client`, `Operator`, `Admin`;
* не содержать доменных правил, которые должны выполняться на сервере;
* отображать ошибки API в пользовательском виде без потери `request_id`.

### 5.3. Интерфейс клиента

* вход и регистрация;
* список счетов и карточка счёта;
* создание счёта;
* перевод;
* создание заявок;
* история операций и заявок.

### 5.4. Интерфейс оператора

* список пользователей и карточка пользователя;
* очередь заявок;
* карточка заявки с решением;
* история операций и заявок пользователей.

### 5.5. Интерфейс администратора

* управление справочниками;
* управление режимами работы системы;
* просмотр аудита.

## 6. Нефункциональные требования

### 6.1. Данные и консистентность

* основное хранилище — PostgreSQL;
* идентификаторы сущностей — `uuid`;
* денежные значения — `numeric(38,10)`;
* все временные метки — UTC;
* денежные операции должны выполняться в транзакции БД;
* конкурентный доступ к затрагиваемым счетам должен контролироваться блокировкой строк;
* серверная часть должна использовать синхронную работу с БД в первой версии.

### 6.2. Безопасность

* передача данных должна выполняться только по TLS в рабочей среде;
* пароли должны храниться в виде безопасного хэша;
* `refresh token` должен быть отзывным;
* секреты не должны храниться в репозитории;
* правила доступа должны проверяться на серверной стороне.

### 6.3. Наблюдаемость

* каждый ответ API должен содержать или позволять сопоставить `request_id`;
* логи должны иметь структурированный формат;
* события аудита должны коррелироваться с запросами.

### 6.4. Производительность

* денежная операция должна укладываться в обычный интерактивный отклик;
* списки должны поддерживать пагинацию.

## 7. Критерии приёмки

### 7.1. Регистрация и вход

* при `registration_mode = auto` пользователь создаётся сразу;
* при `registration_mode = manual` до одобрения заявки вход невозможен;
* вход работает по `username`, `email` и `phone_number`;
* внешний клиент может получить текущего пользователя через API.

### 7.2. Счета

* нельзя создать второй счёт того же типа в той же валюте для одного пользователя;
* счёт нельзя закрыть при ненулевом балансе;
* после закрытия счёт недоступен для новых операций.

### 7.3. Переводы

* успешный перевод изменяет балансы обоих счетов и создаёт две проводки;
* перевод на тот же счёт запрещён;
* перевод с превышением доступного лимита отклоняется.

### 7.4. Пополнение и вывод

* пополнение и вывод проходят только через заявку;
* одобрение заявки создаёт финансовую операцию;
* отклонение заявки не создаёт проводок;
* `Withdraw` не уводит счёт в минус.

### 7.5. Идемпотентность и аудит

* повторный изменяющий запрос с тем же `Idempotency-Key` не создаёт дубликат;
* каждое значимое действие попадает в аудит.

### 7.6. Внешние клиенты

* основные сценарии проходят через консольный клиент;
* веб-приложение использует тот же API, что и консольный клиент;
* серверная часть не содержит отдельного закрытого пути для обхода API клиентами.
