# CLAUDE.md

**Read [AGENTS.md](AGENTS.md) first.** It is the source of truth for architecture, conventions, AI rules, commands and the Definition of Done. This file only adds Claude-specific working habits.

## How to work here

- **Small steps.** Plan briefly, change one layer or feature at a time, run the checks, then move on. Prefer several small commits to one big one.
- **Always run tests and linters before saying a task is done**: the full backend and frontend check lists in AGENTS.md §11. If something fails, fix it or report it clearly. Never hide a failure (e.g. a `| tail` that swallows the exit code).
- **Don't add dependencies without a reason.** Check what is already installed (`pyproject.toml`, `package.json`) first. If a new package is really needed, say why in the commit body and add it to `requirements*.txt` **and** `pyproject.toml` (backend) or via `npm install` (frontend).
- **Respect the layers.** Before writing backend code, decide which layer it belongs to (AGENTS.md §3). Routers stay thin and services never import FastAPI.
- **LLM never computes numbers** (AGENTS.md §5). If you're about to put a calculation in a prompt, stop and put it in `services/` instead.
- **Keep contracts in sync**: when you touch `backend/app/schemas/`, update `frontend/src/types/` and `frontend/src/lib/validators.ts`, and the other way round.
- **Check versions before relying on memory.** Libraries here are recent (Vite 8, Vitest 5, MSW 3, TypeScript 6, Tailwind 4, ESLint 10). If an API looks unfamiliar, read the installed package's types in `node_modules`/`.venv` instead of guessing.
- **Don't touch** `ecoroute.db`, `.env`, `.venv/`, `node_modules/`, or `dist/`. Don't push, and don't rewrite published history.

## Environment notes

- The developer works on **Windows / PowerShell**. Give commands that work in PowerShell (`;` not `&&` in Windows PowerShell 5.1; `.\.venv\Scripts\...`).
- The backend targets Python 3.12 (CI). Any local Python >= 3.12 is fine.
- Line endings are LF (`.gitattributes`). Don't introduce CRLF.
- Run Vitest from PowerShell (or a `C:\...` path). From Git Bash in `/c/...` every suite fails with "Vitest failed to find the runner" (Vitest gets loaded twice under two drive-letter spellings). It is not a code bug.
