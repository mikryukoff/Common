# AGENTS.md

Шаблон-заготовка **Common** для новых проектов. Стек: Python 3.13 + FastAPI +
MySQL + uv. Все проекты используют одну слоистую структуру; при старте нового
проекта шаблон копируется в него как есть.

Документация: `README.md`.

## Стек

- Python **3.13**, пакетный менеджер **`uv`**, FastAPI + Uvicorn.
- MySQL + SQLAlchemy **async** (`aiomysql`) + Alembic.
- Docker: multi-stage, база `python:3.13-slim`.

Импорты всегда от корня репозитория: `backend.app.*` (`PYTHONPATH=/app` в Docker).

## Команды

```bash
uv sync --group dev              # зависимости + тесты
uv lock                          # после правок pyproject.toml
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest -q
uv run alembic -c backend/alembic.ini upgrade head
docker compose up -d --build
```

- UI: `http://localhost:8000/`
- OpenAPI: `http://localhost:8000/docs`
- Backend снаружи — `127.0.0.1:8001` (под Nginx TLS). Adminer — профиль `tools`.

## Карта репозитория

```
backend/app/api/            # HTTP-слой: роутеры, схемы, DI, обработчики ошибок
backend/app/application/    # сервисы: оркестрация use-case'ов, транзакции, jobs
backend/app/domain/         # чистая бизнес-логика (без фреймворков и I/O)
backend/app/infrastructure/ # I/O: БД, репозитории, внешние API, файлы, экспорт
backend/app/security/       # аутентификация, авторизация, шифрование, rate limit
backend/app/config/         # загрузка конфигурации из .env
backend/app/shared/         # утилиты: логирование, базовые ошибки, пути, нормализация
backend/tests/              # pytest; conftest задаёт тестовое окружение
backend/alembic/            # миграции БД
backend/scripts/            # одноразовые скрипты (не runtime)
frontend/                   # статика: html + js + css
data/                       # логи, вспомогательные файлы, не код
deploy/                     # nginx / certbot / скрипты сервера
```

**Правило зависимостей:** `api → application → domain ← infrastructure`.
Никаких обратных импортов: `domain` не знает про FastAPI и БД.

## Назначение слоёв

- **api** — принимает HTTP-запросы, валидирует вход/выход через схемы, вызывает `application`. Без бизнес-логики и работы с БД.
- **application** — оркестрация: `domain` + `infrastructure`, транзакции, jobs, фоновые задачи.
- **domain** — чистые модели и правила предметной области. Без HTTP, БД, фреймворков.
- **infrastructure** — внешний мир: БД, файлы, сторонние API, экспорт документов.
- **security** — аутентификация, авторизация, шифрование, rate limit.
- **config** — единая точка загрузки настроек из окружения.
- **shared** — сквозные утилиты без бизнес-смысла.

Новый endpoint: схема в `api/schemas/`, хендлер в `api/routers/`, логика в
`application/`, доступ к БД — через репозиторий. Сборка сервисов — в
`api/dependencies.py`.

## Контракт ошибок

Прикладные ошибки — подклассы `ApplicationError`
(`backend/app/shared/exceptions.py`, доменные — в
`backend/app/application/exceptions.py`) со стабильными `error_code`,
`status_code`, `details`. Ловятся в `register_exception_handlers`, ответ —
`ErrorResponse`. Не глотать исключения пустым `except` и не отдавать
произвольный `dict` вместо контракта.

`ENVIRONMENT=production` блокирует дефолтные секреты и небезопасные флаги.
Не ослаблять это «для удобства».

## Правила Cursor

Детальные правила вынесены в `.cursor/rules/` и подгружаются по мере
необходимости:

- `000-core.mdc` — стиль, запреты, git (always apply).
- `100-python.mdc` — импорты, логирование, обработка ошибок.
- `110-fastapi.mdc` — роутеры, схемы, DI, auth.
- `120-domain.mdc` — правила чистого доменного слоя.
- `200-tests.mdc` — pytest, фикстуры, маркеры.
- `210-migrations.mdc` — Alembic, работа с БД через репозитории.
- `300-docker.mdc` — Dockerfile, docker-compose, .dockerignore.