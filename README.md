# Common

Шаблон FastAPI-проекта со слоистой архитектурой. Копируйте репозиторий как
заготовку для новых сервисов.

- Для агентов: [`AGENTS.md`](AGENTS.md)
- Cursor rules: [`.cursor/rules/`](.cursor/rules/)

## Стек

- Python 3.13, `uv`, FastAPI, Uvicorn
- MySQL 8 + SQLAlchemy async (`aiomysql`) + Alembic
- Auth: httpOnly cookies (access/refresh JWT)
- Frontend: статика в `frontend/`, раздаётся FastAPI

## Новый проект из шаблона

1. Скопируйте каталог Common в новый репозиторий (или `git clone` и смените
   remote).
2. В `pyproject.toml` задайте `name` и `description` проекта.
3. В `.env` (из `.env.example`):
   - `PROJECT_NAME`, `DB_*`, секреты JWT
   - для локального uvicorn без Docker: `DB_HOST=localhost`
   - `COMPOSE_PROJECT_NAME=myapp` — чтобы несколько проектов не конфликтовали
4. При необходимости поправьте `frontend/` (название в `index.html`).
5. Добавьте доменные модели, сервисы, роутеры и Alembic-ревизии.
6. MCP (опционально): `cp .cursor/mcp.json.example .cursor/mcp.json` и настройте.

```bash
cp .env.example .env
# отредактируйте .env
uv sync --group dev
uv run pytest -q
docker compose up -d --build
```

## Быстрый старт (локально)

```bash
cp .env.example .env
uv sync --group dev
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Нужен доступный MySQL (`DB_*` в `.env`). Без БД поднимутся только статика и
`/health`; bootstrap-админ и auth требуют MySQL.

- UI: http://localhost:8000/
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/health

Bootstrap-админ создаётся при старте из `BOOTSTRAP_ADMIN_*`.

## Docker

```bash
cp .env.example .env
# задайте пароли и секреты; COMPOSE_PROJECT_NAME=myapp
docker compose up -d --build
```

- Backend снаружи: `127.0.0.1:8001` (под Nginx)
- Adminer: `docker compose --profile tools up -d`
- Миграции: `RUN_MIGRATIONS=true` в `.env` (entrypoint)

## Тесты

```bash
uv sync --group dev
uv run pytest -q
```

Юнит-тесты не требуют живой MySQL.

## Структура

```
backend/app/api/            # роутеры, схемы, DI, exception handlers
backend/app/application/    # use-case сервисы, jobs
backend/app/domain/         # чистая бизнес-логика
backend/app/infrastructure/ # БД, репозитории, файлы
backend/app/security/       # JWT/cookies, пароли, rate limit
backend/app/config/         # load_config() из .env
backend/app/shared/         # логирование, ошибки, пути
frontend/                   # html + js + css
deploy/                     # nginx example
```

Правило зависимостей: `api → application → domain ← infrastructure`.

## Новый endpoint

1. Схема в `backend/app/api/schemas/`
2. Хендлер в `backend/app/api/routers/`
3. Логика в `backend/app/application/`
4. БД через репозиторий в `infrastructure/`
5. Сборка сервисов в `api/dependencies.py`
6. При смене схемы БД — Alembic-ревизия
