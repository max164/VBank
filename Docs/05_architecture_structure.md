# VBank — архитектура и структура проекта

## 1. Архитектурный обзор

VBank состоит из трёх основных частей:

* `server` — серверное приложение с программным интерфейсом и прикладной логикой;
* `client` — настольное приложение;
* `database` — PostgreSQL.

## 2. Корневая структура репозитория

```text
vbank/
├── docs/
│   ├── 01_domain_analysis.md
│   ├── 02_technical_assignment.md
│   ├── 03_domain_model.md
│   ├── 04_data_model.md
│   ├── 05_architecture_structure.md
│   ├── 06_domain_glossary.md
│   ├── 07_roadmap.md
│   ├── 08_backlog-1.md
│   ├── 08_backlog-2.md
│   ├── 08_backlog-3.md
│   └── 10_changelog.md
├── server/
├── client/
├── pom.xml
├── .editorconfig
├── .gitignore
└── VERSION
```

## 3. Структура серверной части

```text
server/src/main/java/vbank/
├── bootstrap/
├── auth/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── user/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── account/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── transaction/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── request/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── dictionary/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── setting/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
└── audit/
    ├── api/
    ├── application/
    ├── domain/
    └── infrastructure/
```

### Назначение слоёв

* `api` — контроллеры программного интерфейса, входные и выходные модели, преобразование ошибок;
* `application` — прикладные сценарии и границы транзакций;
* `domain` — сущности, инварианты и интерфейсы репозиториев;
* `infrastructure` — работа с БД, безопасность, конфигурация и интеграция с используемой платформой.

## 4. Структура настольного приложения

```text
client/src/main/java/vbank/
├── bootstrap/
├── auth/
├── dashboard/
├── account/
├── transaction/
├── request/
├── dictionary/
├── setting/
├── audit/
└── shared/
```

### Правило для `shared`

В `shared` допускаются только общие элементы интерфейса, навигация, форматтеры и диалоги. Доменные правила и прикладная логика туда не выносятся.

## 5. Архитектурные правила

### 5.1. Модульность

* верхний уровень делится по контекстам предметной области, а не по ролям пользователей;
* роли `Client`, `Operator`, `Admin` управляют доступом, но не образуют отдельные модули.

### 5.2. Транзакции

* денежные сценарии завершаются в слое `application`;
* работа с балансом и проводками выполняется в одной транзакции БД;
* конкурентный доступ к затрагиваемым счетам контролируется блокировкой строк.

### 5.3. Источник правил

* предметные правила задаются в `03_domain_model.md`;
* физическая схема хранения задаётся в `04_data_model.md`;
* архитектурный документ не дублирует доменные и табличные правила.

## 6. Ресурсы и миграции

```text
server/src/main/resources/
├── application.yaml
├── db/
│   ├── migration/
│   └── seed/
└── logback.xml
```

### Правила

* миграции только вперёд;
* `seed` содержит только обязательные справочники и режимы работы системы;
* секреты не хранятся в репозитории.

## 7. Тестовая структура

```text
server/src/test/java/vbank/
├── auth/
├── user/
├── account/
├── transaction/
├── request/
├── dictionary/
├── setting/
└── audit/
```

### Минимальный набор тестов

* модульные тесты доменных инвариантов;
* интеграционные тесты денежных сценариев;
* проверочные тесты ключевых сценариев программного интерфейса.

