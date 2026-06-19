# Серверная часть VBank

Серверная часть — Python-приложение FastAPI. Каркас этой задачи задаёт структуру
каталогов, зависимости, настройки и локальный запуск. Прикладные маршруты
`/api/v1`, миграции и доменные сценарии добавляются отдельными задачами этапа 3.

## Настройка

Команды выполняются из корня репозитория.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

В `.env` укажите локальный `VBANK_DATABASE_URL`. Пример из `.env.example`
использует учебные значения и не является секретом.

## Запуск

```powershell
python -m vbank
```

Для режима с автоперезапуском:

```powershell
python -m uvicorn vbank.main:app --reload
```

Проверка запуска:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```
