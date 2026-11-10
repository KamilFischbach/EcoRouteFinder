# AGENTS.md

Instructions for AI coding agents (and humans) working on **EcoRoute**. Read this file before changing code. If a rule here conflicts with a habit of yours, this file wins.

## 1. What this project is

EcoRoute compares ways to travel a route (petrol car, EV, train, coach, plane, bike) by **time, cost and kg CO₂**. Users save trips to a history (CRUD). Planned next: a comparison page, a dashboard with charts, and AI features running on a **local Ollama** model (free-text trip parser and a tool-calling advisor), always with a rule-based fallback.

Status: the foundation is done (Trip CRUD from DB to UI, tests, CI). Emissions, routing, weather, AI, charts and the map are **skeletons with `TODO`s**. Do not treat them as implemented.

## 2. Repository map

```
backend/                 FastAPI + SQLModel + SQLite (Python 3.12)
  app/main.py            create_app(): CORS, error handlers, routers. `app` = ASGI entrypoint
  app/core/config.py     Settings (env vars / .env): DATABASE_URL, CORS_ORIGINS, OLLAMA_*, AI_ENABLED
  app/core/errors.py     Domain errors (AppError, NotFoundError). No HTTP here
  app/db.py              engine, get_session (dependency), init_db (create tables at startup)
  app/models/            SQLModel table models (DB shape only)
  app/schemas/           Pydantic DTOs: request/response contracts + validation (TripCreate/Update/Read)
  app/repositories/      DB access. The ONLY layer that uses Session
  app/services/          Business logic. emissions.py / routing.py / weather.py are TODO stubs
  app/ai/                llm_client.py (LLMClient Protocol), prompts.py, trip_parser.py, advisor_agent.py
  app/api/deps.py        Dependency wiring: session -> repository -> service
  app/api/error_handlers.py  Exception -> JSON error mapping
  app/api/v1/            Routers: health.py, trips.py
  tests/conftest.py      In-memory SQLite, get_session override, TestClient
  tests/api/             HTTP-level tests      tests/unit/  service/pure-logic tests
frontend/                Vite + React 19 + TypeScript (strict) + Tailwind 4
  src/api/               fetch client (apiFetch, ApiError), endpoint functions, error -> message
  src/components/        Shared, domain-agnostic UI (Button, Card, ConfirmDialog, Layout, ...)
  src/features/trips/    Trip feature: hooks (TanStack Query), form, validation, table
  src/pages/             Route-level components: TripsPage, ComparePage, DashboardPage (placeholders)
  src/lib/               Small helpers: cn, format, styles
  src/types/             Shared TS types mirroring backend schemas
  src/test/              Vitest setup, MSW server + handlers, render helpers
.github/workflows/ci.yml Backend + frontend jobs (lint, format, types, tests, build)
```

## 3. Backend architecture rules

Request flow: **router → service → repository → DB**. Each layer only calls the one below it.

| Layer | Does | Must NOT |
|---|---|---|
| `api/v1/*` (router) | Parse input (DTOs), call one service method, return `XxxRead` | Touch `Session`, run queries, contain `if` business rules, catch domain errors |
| `api/deps.py` | Build services from repositories via `Depends` | Contain logic |
| `services/` | Business rules, orchestration, raise `AppError` subclasses | Import FastAPI, raise `HTTPException`, know status codes, build queries |
| `repositories/` | `select`, `add`, `commit`, `refresh`, `delete` | Contain business rules or validation |
| `models/` | Table definitions | Be used as request/response bodies |
| `schemas/` | Input validation and output shape | Do I/O |

More rules:
- **Errors**: services raise `NotFoundError` (or a new `AppError` subclass in `core/errors.py`). Map new error types to status codes in `_DOMAIN_STATUS` in `api/error_handlers.py`. Every error response has the shape `{"error": {"code", "message", "details"}}`. Never return a different shape.
- **Validation** lives in `schemas/` (Pydantic `Field`/`StringConstraints`). Frontend limits in `src/features/trips/validation.ts` must stay in sync. Change both or neither.
- **Config** only via `get_settings()`. No `os.environ` reads elsewhere and no hard-coded URLs or secrets.
- **Time**: store UTC (`models.trip.utc_now`). `TripRead` re-attaches UTC because SQLite drops tzinfo.
- **New endpoint checklist**: DTOs in `schemas/` → repository method → service method → router in `api/v1/` → register in `api/v1/__init__.py` → API test + unit test.
- **No migrations yet**: tables are created by `init_db()` at startup. After changing a model locally, delete `backend/ecoroute.db`. Introduce Alembic before the first schema change that must keep data.

## 4. Frontend architecture rules

- Components are **function components** with typed props (`interface XxxProps`). No class components, no default exports (except config files).
- **Data fetching only through hooks** in `features/<feature>/useXxx.ts` built on TanStack Query. Components never call `fetch` or `apiFetch` directly.
- HTTP goes through `src/api/client.ts` (`apiFetch`). Base URL comes from `VITE_API_URL`. Endpoint functions live in `src/api/<resource>.ts`.
- Query keys come from a key factory (`tripKeys`). Mutations invalidate `tripKeys.all` instead of hand-editing the cache.
- Every data view handles **loading, empty and error** states (`Spinner`, `EmptyState`, `ErrorState`). User-facing error text comes from `getErrorMessage()`.
- Pure logic (validation, mapping, formatting) goes in `.ts` files next to the feature and gets unit tests. `.tsx` files export components only (enforced by `react-refresh/only-export-components`).
- Styling: Tailwind utility classes only, no CSS modules or inline `style`. Palette: `emerald`/`lime` accents on `stone`/white. Mobile-first: make it work at 375px, then add `sm:`/`md:`/`lg:`.
- Accessibility: every input has a `<label>`; errors are linked with `aria-invalid` and `aria-describedby`; icon-only buttons get `aria-label`. Tests query by role/label, so this is enforced.
- Everything is in **English**: UI copy, code, comments and identifiers.
- `recharts` and `react-leaflet` are installed for the dashboard and map. Use them there; do not add other chart or map libraries.

## 5. AI rules (non-negotiable)

1. **The LLM never calculates.** CO₂, cost, distance and time always come from deterministic code (`services/emissions.py`, `routing.py`, `weather.py`). The LLM extracts structured data or chooses tools, then explains results it was given.
2. **Always a fallback.** Every AI feature must work without Ollama: `trip_parser` falls back to `parse_trip_with_rules`; the advisor falls back to a templated answer built from service results. `/health` reports `ai_available`.
3. **Depend on `LLMClient` (Protocol), not on Ollama.** Inject the client; tests use a fake client and never call the network.
4. **Prompts live only in `app/ai/prompts.py`** as versioned constants (`XXX_V1`). No prompt strings in services, routers or tests.
5. **Structured output is validated.** Pass a JSON schema (from the Pydantic model's `model_json_schema()`) and validate the reply with that model. Invalid output means fallback, not a crash.
6. Tool calls are bounded (`MAX_STEPS`) and tool arguments are validated before execution.
7. Model and host come from settings (`OLLAMA_HOST`, `OLLAMA_MODEL`, default `qwen2.5:7b`). Respect `AI_ENABLED=false`.

## 6. Naming conventions

| What | Convention | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `trip_service.py`, `list_trips()` |
| Python classes | `PascalCase` | `TripService`, `TripRepository` |
| DTOs | `<Entity>Create` / `<Entity>Update` / `<Entity>Read` | `TripCreate` |
| Repositories / services | `<Entity>Repository` / `<Entity>Service` | |
| Constants | `UPPER_SNAKE_CASE` | `ADVISOR_TOOLS` |
| Python tests | `tests/<api|unit>/test_<module>.py`, `test_<behaviour>()` | `test_get_missing_trip_returns_404` |
| React components + files | `PascalCase.tsx` | `TripForm.tsx` |
| Hooks | `useXxx` in `useXxx.ts` | `useTripsQuery` |
| Other TS files | `camelCase.ts` | `validation.ts` |
| TS tests | next to the code, `*.test.ts(x)` | `TripForm.test.tsx` |
| API paths | plural nouns, kebab-case, under `/api/v1` | `/api/v1/trips/{id}` |
| JSON fields | `snake_case` (same as backend) | `distance_km` |

## 7. Code style

- **Type hints everywhere** (mypy `strict`). No `Any` unless the data really is untyped (e.g. raw JSON), and never `# type: ignore` without a reason in the comment.
- TypeScript `strict` + `noUncheckedIndexedAccess`. No `any`; use `unknown` and narrow it.
- **Small functions**: one job each, roughly 30 lines or less. Extract a helper before nesting deeper than 2 levels.
- **No logic in routers or JSX.** Move it to services or to `.ts` helpers.
- Formatting is automatic: `ruff format` (line length 100) and Prettier (single quotes, semicolons, width 100). Don't hand-format or argue with the formatter.
- Comments explain *why*, not *what*. Use `TODO(<area>): ...` for planned work, e.g. `TODO(emissions)`.
- No new dependency without a one-line justification in the commit body. Prefer the standard library and what's already installed.

## 8. Tests

Every new piece of logic ships with tests in the same commit:
- **Backend**: an API test for each endpoint status path (success, 404, 422, ...) in `tests/api/`, and unit tests for service and pure logic in `tests/unit/`. Use the `client`/`session` fixtures from `conftest.py` (in-memory SQLite). Never touch `ecoroute.db` or the network in tests.
- **Frontend**: React Testing Library + `user-event`, querying by role or label. Mock HTTP only with MSW (`src/test/handlers.ts`, override per test with `server.use`). Don't mock hooks or `fetch` directly. MSW 3 option name: `onUnhandledFrame` (not `onUnhandledRequest`).
- AI code: test with a fake `LLMClient`, covering both the LLM path and the fallback path.
- Bug fix = a failing test first, then the fix.

## 9. Commands

PowerShell (Windows). The bash equivalents are the same except for venv activation (`source .venv/bin/activate`).

```powershell
# Backend (from backend/)
py -3.12 -m venv .venv               # once; any Python >= 3.12 works
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # API on http://localhost:8000, docs at /docs
ruff check . ; ruff format --check . ; mypy app ; pytest
ruff check --fix . ; ruff format .   # auto-fix

# Frontend (from frontend/)
npm install
npm run dev                          # http://localhost:5173
npm run lint                         # eslint + prettier --check
npm run typecheck                    # tsc --noEmit
npx vitest run                       # tests once (npm test = watch mode)
npm run build
npm run format                       # auto-format
```

## 10. Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): imperative summary`, at most 72 characters, lowercase.

- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `chore`, `perf`, `build`.
- Scopes: `api` (backend HTTP/services), `db`, `ai`, `web` (frontend), `ci`, `docs`, `deps`.
- One logical change per commit, and tests go in the same commit as the code they cover.
- Examples: `feat(api): add trip CRUD`, `feat(ai): add rule-based trip parser fallback`, `fix(web): keep form values after server error`.
- Never commit `.env`, `*.db`, `node_modules`, `.venv` or build output. Never push without being asked.

## 11. Definition of Done

A task is done only when all of these are true:

- [ ] Backend: `ruff check .`, `ruff format --check .`, `mypy app` and `pytest` pass.
- [ ] Frontend: `npm run lint`, `npm run typecheck`, `npx vitest run` and `npm run build` pass.
- [ ] New logic has tests (both success and failure paths).
- [ ] Layer rules (section 3/4) and AI rules (section 5) are respected.
- [ ] Backend and frontend contracts are in sync (`schemas/*.py` ↔ `src/types/*.ts`, validation limits).
- [ ] New config is in `Settings` **and** `.env.example`. New commands are in the README.
- [ ] UI changes handle loading, empty and error states, and work at mobile width.
- [ ] Committed with a Conventional Commit message. No stray TODOs without an area tag.
