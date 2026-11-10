# EcoRoute

[![CI](https://github.com/KamilFischbach/EcoRouteFinder/actions/workflows/ci.yml/badge.svg)](https://github.com/KamilFischbach/EcoRouteFinder/actions/workflows/ci.yml)

**EcoRoute compares ways to travel the same route by time, cost and carbon footprint.** Enter where you start, where you're going and how many people are travelling. EcoRoute compares a petrol car, an electric car, train, coach, plane and bike, and lets you keep a history of your trips.

> **Status:** trip history, CO₂ per trip and the mode comparison work end to end. The dashboard, map and AI features are scaffolded and coming next.

A local LLM (via [Ollama](https://ollama.com)) will parse free-text trips and act as an advisor. The core rule: **the LLM never calculates emissions.** Deterministic code does the maths; the model only picks tools and explains the results. Every AI feature has a rule-based fallback, so the app works without a model.

## Features

- [x] Trip history: add, edit, delete (with confirmation), filter by transport mode, CO₂ per person for each trip
- [x] Mode comparison: time, cost and kg CO₂ per person for six modes, with Greenest / Fastest / Cheapest picks, a CO₂ chart and one-click "Save trip"
- [x] Real routes from OpenStreetMap (Nominatim + OSRM) with an offline fallback estimate
- [x] REST API with validation and a consistent error format
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
    services/          # business logic: trips, comparison, emissions + factors, routing (weather: stub)
    ai/                # LLM client interface, prompts, parser and advisor skeletons
    api/v1/            # routers: health, trips, comparisons
  tests/               # api/ and unit/ tests (in-memory SQLite)
frontend/
  src/
    api/               # fetch client, endpoint functions
    components/        # shared UI components
    features/trips/    # trip form, table, validation, TanStack Query hooks
    features/compare/  # compare form, results cards, CO2 chart
    lib/               # formatting, shared validators, helpers
    pages/             # Trips, Compare, Dashboard (placeholder)
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
| `GEOCODER_URL` | `https://nominatim.openstreetmap.org` | backend `.env` |
| `ROUTING_URL` | `https://router.project-osrm.org` | backend `.env` |
| `HTTP_TIMEOUT_S` | `8` | backend `.env` |
| `HTTP_USER_AGENT` | `EcoRoute/0.1 (+https://github.com/KamilFischbach/EcoRouteFinder)` | backend `.env` |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | frontend `.env.local` |

`HTTP_USER_AGENT` identifies the app to Nominatim, as its [usage policy](https://operations.osmfoundation.org/policies/nominatim/) requires. If you deploy EcoRoute, set your own value (a URL, not an email).

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | `{status, ai_available}` |
| `GET` | `/api/v1/trips?mode=` | List trips, newest first, optional mode filter |
| `POST` | `/api/v1/trips` | Create a trip → `201` |
| `GET` | `/api/v1/trips/{id}` | Get one trip → `404` if missing |
| `PUT` | `/api/v1/trips/{id}` | Update the fields sent in the body |
| `DELETE` | `/api/v1/trips/{id}` | Delete → `204` |
| `POST` | `/api/v1/comparisons` | Compare all modes for `{origin, destination, passengers, distance_km?}`. Stores nothing |

Errors always use one shape: `{"error": {"code": "NOT_FOUND", "message": "...", "details": ...}}`. Codes are upper case: `NOT_FOUND`, `VALIDATION_ERROR`, `UNKNOWN_PLACE` (422), `ROUTE_TOO_SHORT` (422), `SERVICE_UNAVAILABLE` (503), `INTERNAL_ERROR`.

## How emissions are calculated

All the maths is in [`backend/app/services/emissions.py`](backend/app/services/emissions.py); every factor and its source is in [`transport_factors.py`](backend/app/services/transport_factors.py). No LLM is involved.

**Everything is per person.** For cars, the vehicle's CO₂ and cost are split between the passengers. Train, coach and plane factors already apply per passenger-km, so they don't depend on group size. "Saved vs driving alone" compares each option with one person in a petrol car on the same route.

| Mode | CO₂ factor | Source |
|---|---|---|
| Petrol car | 0.16152 kg CO₂e per vehicle-km | DESNZ 2026, average petrol car |
| Electric car | ≈0.113 kg CO₂ per vehicle-km | 0.205 kWh/km (implied by DESNZ 2026 BEV factor ÷ UK grid factor) × 0.553 kg CO₂/kWh (KOBiZE, Polish grid, 2024 data, published Dec 2025) |
| Train | 0.03092 kg CO₂e per passenger-km | DESNZ 2026, UK national rail |
| Coach | 0.03948 kg CO₂e per passenger-km | DESNZ 2026, coach |
| Plane | 0.22928 kg CO₂e per passenger-km | DESNZ 2026, domestic flight, average passenger, **with radiative forcing (RFI)** |
| Bike | 0 | - |

DESNZ = UK Department for Energy Security and Net Zero, [GHG conversion factors 2026](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026) (flat file, revised July 2026). Direct emissions only: well-to-tank (fuel production) is excluded for every mode.

**Assumptions and simplifications**

- The train factor is the UK average. Polish electric rail runs on a more coal-heavy grid, so real train emissions in Poland are likely higher. Treat the number as an approximation.
- One flight factor (domestic) is used for all distances. Longer flights have lower per-km factors, so long flights are overestimated.
- EV emissions use the average Polish grid, not the time of charging or a home solar setup.
- Costs (PLN/km) and speeds are rough estimates marked `approx.` in the code: fuel or electricity only for cars (no depreciation, tolls or parking), typical fares for public transport. Times add a fixed overhead: 15 min for train and coach, 120 min for the airport.
- Practical limits: bikes over 100 km and flights under 300 km are marked "not practical"; a car takes at most 5 people. Greenest / Fastest / Cheapest are picked only from practical options.

## Route data and fallback

1. **Geocoding:** place names are looked up with [Nominatim](https://nominatim.org) (OpenStreetMap). Results are cached in memory, and requests are throttled to 1 per second as its usage policy asks.
2. **Driving route:** distance and driving time come from the public [OSRM](https://project-osrm.org) server.
3. **Distance per mode:** cars and coach use the road distance. Train, bike and plane use the straight-line (great-circle) distance × a detour factor (train 1.2, bike 1.2, plane 1.0 because DESNZ flight factors are meant for great-circle distance).
4. **Fallbacks:**
   - OSRM down or no route: road distance = straight-line distance × 1.25, shown with an **estimated** badge.
   - A place can't be found: `UNKNOWN_PLACE` (422).
   - Nominatim unreachable: `SERVICE_UNAVAILABLE` (503). The UI suggests entering the distance by hand.
   - User enters a distance under **Advanced**: no network calls at all.

Public Nominatim and OSRM servers are fine for a demo but not for heavy traffic. For production, point `GEOCODER_URL` / `ROUTING_URL` at your own instances.

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
