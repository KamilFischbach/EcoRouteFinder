# EcoRoute: technical details

How EcoRoute works and why it is built this way. For what the app does and how to run it, see the [README](README.md).

## Contents

- [Architecture](#architecture)
- [Configuration](#configuration)
- [API](#api)
- [How emissions are calculated](#how-emissions-are-calculated)
- [Routes and fallbacks](#routes-and-fallbacks)
- [Comparison history](#comparison-history)
- [Dashboard](#dashboard)
- [AI features](#ai-features)
- [MCP server](#mcp-server)
- [Tests and CI](#tests-and-ci)
- [Trade-offs and what I'd do next](#trade-offs-and-what-id-do-next)

## Architecture

```
backend/   FastAPI + SQLModel + SQLite (Python 3.12)
  app/api/v1/        routers: thin, parse input, call one service, return a DTO
  app/services/      business logic and all maths (no FastAPI imports)
  app/repositories/  the only layer that talks to the database
  app/models/        database tables          app/schemas/  request/response DTOs + validation
  app/ai/            LLM client, prompts, tool registry, trip parser, EcoAdvisor
  app/mcp_server.py  MCP server over the same tool registry
frontend/  React 19 + TypeScript + Vite + TanStack Query + Tailwind 4 + Recharts
  src/features/      one folder per feature (trips, compare, assistant, dashboard, mcp)
  src/api/           fetch client and endpoint functions; components never call fetch
```

- **Request flow:** router → service → repository → database. Each layer calls only the one below. Domain errors are raised in services and mapped to HTTP codes in one place, so every error has the same JSON shape.
- **Why this split:** services take plain values and return dataclasses. The REST API, the AI agent and the MCP server reuse them without HTTP in the way.
- **Frontend:** data goes through TanStack Query hooks. Pure logic (validation, formatting, text rules) lives in `.ts` files with unit tests, and `.tsx` files only render.
- **Rules for contributors and AI agents** are in [AGENTS.md](AGENTS.md).

## Configuration

Everything works with the defaults; see `backend/.env.example` and `frontend/.env.example`.

| Variable | Default | What it does |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./ecoroute.db` | SQLite file, created on first start |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins (comma-separated) |
| `AI_ENABLED` | `true` | `false` = never contact Ollama, rules only |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `http://localhost:11434` / `qwen3:8b` | Local LLM |
| `GEOCODER_URL` / `ROUTING_URL` / `WEATHER_URL` | public Nominatim / OSRM / Open-Meteo | External data, no API keys |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Frontend → API |

Older databases are upgraded in place on startup (small idempotent steps in `db.py`), so nobody has to delete their data after a schema change.

## API

REST under `/api/v1`, interactive docs at `http://localhost:8000/docs`.

| Resource | Endpoints |
|---|---|
| Trips | `GET /trips?mode=`, `POST /trips`, `GET /trips/{id}`, `PATCH /trips/{id}` (partial update), `DELETE /trips/{id}` |
| Comparisons | `POST /comparisons`, `GET /comparisons`, `GET /comparisons/{id}`, `DELETE /comparisons/{id}` |
| Advice | `POST /comparisons/{id}/advice` (always `200`: AI or rule-based) |
| Trip parser | `POST /trip-drafts` (text → form fields; stores nothing) |
| Statistics | `GET /stats?range=30d\|90d\|12m\|all` |
| Health | `GET /health` (also reports whether the AI is available) |

- Status codes: `201` on create, `204` on delete, `404` if missing, `422` for invalid input, `503` when a map service is down.
- Errors always look like `{"error": {"code": "NOT_FOUND", "message": "...", "details": ...}}`.
- A trip's `travelled_on` defaults to today; planned trips may be up to a year ahead.

## How emissions are calculated

All maths is in `services/emissions.py`; every factor and its source is in `services/transport_factors.py`. No LLM is involved.

- **Everything is per person.** A car's CO₂ and cost are split between passengers. Train, coach and plane factors are already per passenger.
- **CO₂ saved** compares each option with **the same group going together by petrol car**. Example: 2 people, 293 km. The car is 23.7 kg each and the train 9.3 kg, so the train saves 14.3 kg per person. Comparing with "one person driving alone" would overstate the saving.

| Mode | CO₂ factor | Source |
|---|---|---|
| Petrol car | 0.16152 kg per vehicle-km | DESNZ 2026 |
| Electric car | ≈0.113 kg per vehicle-km | 0.205 kWh/km × Polish grid 0.553 kg/kWh (KOBiZE) |
| Train | 0.03092 kg per passenger-km | DESNZ 2026 (UK rail) |
| Coach | 0.03948 kg per passenger-km | DESNZ 2026 |
| Plane | 0.22928 kg per passenger-km | DESNZ 2026, domestic flight, with radiative forcing |
| Bike | 0 | - |

**Simplifications I chose on purpose:** UK rail stands in for Polish rail, one flight factor for all distances, and the average Polish grid for EVs. Costs and speeds are rough estimates. A bike over 100 km and a flight under 300 km count as "not practical".

## Routes and fallbacks

1. Place names → coordinates with Nominatim (cached, max 1 request/s, as its policy asks).
2. Road distance and driving time from OSRM. Train, bike and plane use the straight-line distance × a detour factor.
3. Fallbacks: OSRM down → straight line × 1.25, shown as **estimated**. Unknown place → `422`. Geocoder down → `503`, and the UI suggests typing the distance under **Advanced**, which needs no network at all.

## Comparison history

Every comparison is saved and linkable at `/compare/:id`. The result is stored as a **versioned JSON snapshot**, because emission factors may change and the history should show what the user saw at the time. Opening a saved comparison never recomputes it. A few values are also plain columns, so the history list stays cheap.

## Dashboard

All numbers come from `GET /stats`, computed by a pure function in `services/stats.py`. The UI does not recalculate anything.

- **Footprint** = sum of the trips' CO₂ per person in the range.
- **CO₂ saved** = petrol car for the same group and distance minus the trip. The total is **net**: a flight can make it negative, and the UI then says "12 kg more than going by petrol car".
- **Eco-points** = 10 per kg saved per trip, never negative. **Levels:** Seedling 0, Sprout 250, Sapling 1,500, Tree 4,000, Forest 8,000.
- **Ranges:** 30 and 90 days by week; 12 months and all time by month. Empty periods show as zero. Footprint and savings are compared with the previous period of the same length.
- **Planned trips** (dated in the future) count only once their day comes.
- **Demo data:** `python -m app.seed` adds 30 example trips. It refuses a database that already has trips; `--force` only adds, never deletes.

## AI features

**Rule number one: the LLM never calculates.** Code computes every number; the model extracts data, chooses tools and explains. Every AI feature has a rule-based fallback, so the app works without Ollama.

| Feature | The LLM does | Code does |
|---|---|---|
| Trip parser (`POST /trip-drafts`) | Reads a sentence (English or Polish) and returns route, group size, mode and preferences as JSON | Validates the JSON, checks the places really occur in the text, otherwise falls back to regex rules |
| EcoAdvisor (`POST /comparisons/{id}/advice`) | Calls tools (comparison, emissions, weather), picks one option, writes a short summary | Checks the pick is practical (e.g. no bike with skis or in the rain), writes the reasons from the data, rejects summaries with wrong numbers or false "cheapest/fastest" claims, falls back to rules |

- **Guardrails:** at most 4 tool rounds. Structured output is validated with Pydantic. Numbers the model may quote are ready-made strings ("15.7 kg"). Any failure → rule-based answer.
- **Transparency:** the UI shows whether the answer came from **AI · qwen3:8b** or the rules, plus "How I got this" (the tool calls).
- **Trip assistant:** the frontend chains parse → compare → advise in a hook. Results appear in about a second, and the slower advice fills in when ready. A failed model never hides the numbers.
- **Testable:** the LLM sits behind an interface; tests use a scripted fake and never call Ollama.

## MCP server

The same tools are exposed over the Model Context Protocol, so any AI agent (Claude Desktop, MCP Inspector) can use them. `get_trip_stats` returns the Dashboard's numbers. Tools are defined once, in `ai/tools.py`; the MCP server only adapts them. All MCP tools are read-only.

- **stdio:** `python -m app.mcp_server` (a desktop client starts it itself).
- **HTTP:** `/mcp` on the API. The app's **MCP tools** page is a real MCP client built on the official TypeScript SDK.
- Only local hosts and the configured frontend origins may call `/mcp`.

Claude Desktop example (`claude_desktop_config.json`, with your paths):

```json
{
  "mcpServers": {
    "ecoroute": {
      "command": "C:\\path\\to\\EcoRouteFinder\\backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.mcp_server"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\EcoRouteFinder\\backend",
        "DATABASE_URL": "sqlite:///C:/path/to/EcoRouteFinder/backend/ecoroute.db"
      }
    }
  }
}
```

## Tests and CI

```powershell
# backend/ (venv active)
ruff check . ; ruff format --check . ; mypy app ; pytest
# frontend/
npm run lint ; npm run typecheck ; npx vitest run ; npm run build
```

- **Backend:** API tests for every status path and unit tests for services, all on in-memory SQLite. Fakes stand in for routing, weather and the LLM, so tests never use the network.
- **Frontend:** React Testing Library queries by role and label (accessibility gets tested too), and MSW mocks the API.
- **CI:** GitHub Actions runs all of the above on every push.
- On Windows, run Vitest from PowerShell. From Git Bash in `/c/...` it fails with "Vitest failed to find the runner".

## Trade-offs and what I'd do next

- **SQLite + small upgrade steps instead of a migration tool**, because the task asked for a database that needs no setup. A bigger app would use Alembic and PostgreSQL.
- **A local LLM instead of a cloud API:** free, private and offline, but slower and less accurate, which is why every AI answer is checked and has a fallback.
- **No users or login:** the brief asked for an MVP. Next steps: accounts, then per-user trips and statistics.
- **Approximate factors:** good enough to compare modes, not for official reporting. With more time: Polish rail data, distance-based flight factors, real fares.
- **Next features:** a map of the route, and letting EcoAdvisor use `get_trip_stats` ("this would be your 5th train trip this month").
