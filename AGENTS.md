# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `app/`. Use `app/api` for FastAPI routes, `app/services` for orchestration, `app/engine` for rule execution, `app/models` and `app/repositories` for persistence, and `app/schemas` for request/response models. AI integrations live under `app/ai`, seed content under `app/seeds`, and Alembic migrations under `alembic/versions`. Tests are split by concern in `tests/api`, `tests/domain`, `tests/db`, and `tests/repositories`.

## Build, Test, and Development Commands
- `python -m pip install -r requirements.txt`: install runtime and test dependencies.
- `python -m uvicorn app.main:app --reload`: run the API locally with auto-reload.
- `python -m pytest -q`: run the full test suite.
- `python -m pytest tests/api/test_actions.py -q`: run a focused API file during iteration.
- `python -m alembic upgrade head`: apply database migrations.
- `docker compose up -d`: start local services from `compose.yaml` when needed.

## Coding Style & Naming Conventions
Use Python 3.13 features and 4-space indentation. Keep modules small and responsibility-focused. Prefer explicit names such as `WorldBootstrapService` or `SessionResponse` over abbreviations. Use `snake_case` for functions, variables, and module names; `PascalCase` for classes; and uppercase for constants. Follow existing Chinese docstrings and domain terminology. Keep comments short and only where logic is not obvious.

## Testing Guidelines
This repository uses `pytest` with shared fixtures in `tests/conftest.py`. Name tests `test_<behavior>` and keep them close to the layer they cover. Add or update API tests for contract changes, domain tests for engine/runtime logic, and DB tests for migrations or schema changes. Prefer targeted test runs while iterating, then finish with `python -m pytest -q`.

## Commit & Pull Request Guidelines
Recent history is inconsistent (`change`, merge commits), so prefer clear Conventional Commit-style subjects such as `feat: move runtime text artifacts into database` or `fix: remove session path fields from API`. Keep each commit scoped to one concern. PRs should include a short summary, affected endpoints or tables, migration notes, and the exact verification commands you ran. Add request/response samples when changing API behavior.

## Security & Configuration Tips
Keep secrets in `.env`; do not commit real credentials. Main settings are loaded from `KIRIGIRI_`-prefixed environment variables. Use SQLite for local tests and migrations, and only enable provider-backed OpenAI settings when integration testing requires it.
