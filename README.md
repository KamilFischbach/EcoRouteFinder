# EcoRoute

[![CI](https://github.com/KamilFischbach/EcoRouteFinder/actions/workflows/ci.yml/badge.svg)](https://github.com/KamilFischbach/EcoRouteFinder/actions/workflows/ci.yml)

**EcoRoute compares ways to travel the same route by time, cost and carbon footprint.** Enter where you start, where you're going and how many people are travelling. EcoRoute compares a petrol car, an electric car, train, coach, plane and bike, and lets you keep a history of your trips.

> **Status: early foundation.** Trip history (full CRUD) works end to end. The comparison, emissions, charts, map and AI features are scaffolded and coming next.

A local LLM (via [Ollama](https://ollama.com)) will parse free-text trips and act as an advisor. The core rule: **the LLM never calculates emissions.** Deterministic code does the maths; the model only picks tools and explains the results. Every AI feature has a rule-based fallback, so the app works without a model.

## Features

- [x] Trip history: add, edit, delete (with confirmation), filter by transport mode
- [x] REST API with validation and a consistent error format
- [ ] Mode comparison: time, cost, kg CO₂ _(coming soon)_
- [ ] Dashboard: CO₂ over time, kg saved, eco-points _(coming soon)_
- [ ] AI trip parser (structured output) + tool-calling advisor, with rule-based fallback _(coming soon)_

## Creative twist

_Coming soon._

## Tech stack

| Area | Tools |
|---|---|
| Backend | Python 3.12, FastAPI, SQLModel, SQLite, pydantic-settings |
| Backend quality | pytest + httpx, ruff (lint + format), mypy (strict) |
| Frontend | Vite, React 19, TypeScript (strict), React Router, TanStack Query, Tailwind CSS 4 |
| Frontend quality | Vitest, React Testing Library, MSW, ESLint, Prettier |
| Planned | Recharts (dashboard), react-leaflet (map), Ollama + `qwen2.5:7b` (AI) |
| CI | GitHub Actions (parallel backend and frontend jobs) |

## Project structure

```
backend/
  app/
    main.py            # create_app(): CORS, error handlers, routers
    core/              # settings, domain errors
    db.py              # engine, session dependency, init_db
    models/            # SQLModel tables
    schemas/           # request/response DTOs + validation
    repositories/      # database access
    services/          # business logic (+ emissions/routing/weather stubs)
    ai/                # LLM client interface, prompts, parser and advisor skeletons
    api/v1/            # routers: health, trips
  tests/               # api/ and unit/ tests (in-memory SQLite)
frontend/
  src/
    api/               # fetch client, endpoint functions
    components/        # shared UI components
    features/trips/    # trip form, table, validation, TanStack Query hooks
    pages/             # Trips, Compare (placeholder), Dashboard (placeholder)
    types/             # shared TypeScript types
    test/              # Vitest setup, MSW handlers
.github/workflows/ci.yml
AGENTS.md              # rules for AI agents and contributors
CLAUDE.md              # Claude-specific notes (points to AGENTS.md)
```

Architecture: requests flow **router → service → repository → database**. Routers never touch the DB session, and services never know about HTTP. See [AGENTS.md](AGENTS.md) for the full rules.

## Getting started

Requirements: **Python 3.12+**, **Node.js 22+**, Git. Commands are for **PowerShell**; bash variants are in comments.

### 1. Backend (API on http://localhost:8000)

```powershell
cd backend
py -3.12 -m venv .venv                 # bash: python3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1           # bash: source .venv/bin/activate
pip install -r requirements-dev.txt
Copy-Item .env.example .env            # optional, defaults work; bash: cp .env.example .env
uvicorn app.main:app --reload
```

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
- The SQLite file `backend/ecoroute.db` is created on first start.

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip activation and call the venv directly: `.\.venv\Scripts\python -m uvicorn app.main:app --reload`.

### 2. Frontend (app on http://localhost:5173)

In a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local      # optional; bash: cp .env.example .env.local
npm run dev
```

`VITE_API_URL` defaults to `http://localhost:8000/api/v1`.

### 3. Optional: local AI with Ollama

AI features aren't implemented yet, but this is the model they'll use:

```powershell
ollama pull qwen2.5:7b
# then in backend/.env: AI_ENABLED=true (OLLAMA_HOST defaults to http://localhost:11434)
```

### Configuration

| Variable | Default | Where |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./ecoroute.db` | backend `.env` |
| `CORS_ORIGINS` | `http://localhost:5173` (comma-separated) | backend `.env` |
| `OLLAMA_HOST` | `http://localhost:11434` | backend `.env` |
| `OLLAMA_MODEL` | `qwen2.5:7b` | backend `.env` |
| `AI_ENABLED` | `false` | backend `.env` |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | frontend `.env.local` |

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | `{status, ai_available}` |
| `GET` | `/api/v1/trips?mode=` | List trips, newest first, optional mode filter |
| `POST` | `/api/v1/trips` | Create a trip → `201` |
| `GET` | `/api/v1/trips/{id}` | Get one trip → `404` if missing |
| `PUT` | `/api/v1/trips/{id}` | Update the fields sent in the body |
| `DELETE` | `/api/v1/trips/{id}` | Delete → `204` |

Errors always use one shape: `{"error": {"code": "NOT_FOUND", "message": "...", "details": ...}}`.

## Running tests and checks

```powershell
# backend/ (venv active)
ruff check . ; ruff format --check . ; mypy app ; pytest

# frontend/
npm run lint ; npm run typecheck ; npx vitest run ; npm run build
```

CI runs the same steps on every push and pull request.

## How I used AI

_Coming soon._ The rules given to coding agents are in [AGENTS.md](AGENTS.md).

## Demo (GIF)

_Coming soon._

## License

[MIT](LICENSE)
