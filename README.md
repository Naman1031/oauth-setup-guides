# OAuth Setup Guides (working title)

A research and guide tool that helps developers understand the work involved
in setting up OAuth with third-party providers. See `PROJECT_SPEC.md`.

> Status: **Phase 2 of 4**: frontend + FastAPI backend + Supabase database.
> The research agent arrives in Phase 3; the full README in Phase 4.

```text
React (Vite)  ──fetch──▶  FastAPI (/api/...)  ──SQLAlchemy──▶  PostgreSQL (Supabase)
```

## Repository layout

```text
frontend/            React + TypeScript + Vite + Tailwind + shadcn/ui
backend/             FastAPI + Pydantic + SQLAlchemy + Alembic (+ tests)
seed_data/guides/    The six researched guides (one JSON file per application)
PROJECT_SPEC.md      Product specification
CLAUDE_CODE_PROMPT.md  Implementation instructions
DECISIONS.md         Decision / assumption log
```

## Run locally

Requires Python 3.12, Node.js 20.19+ / 22.12+ (developed on Node 26 LTS),
a Supabase project, and (for tests) a local PostgreSQL.

### Backend

```bash
cd backend
py -3.12 -m venv .venv            # Windows; use python3.12 on macOS/Linux
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # then fill in DATABASE_URL (Supabase session pooler)
alembic upgrade head              # create the tables
python -m scripts.seed_applications   # load seed_data/guides/*.json (safe to re-run)
uvicorn app.main:app --reload     # http://localhost:8000/api/health, docs at /docs
```

### Tests

```bash
cd backend
python -m scripts.create_test_database   # once; uses TEST_DATABASE_URL from .env
pytest
```

Tests use only `TEST_DATABASE_URL` (a local database whose name must contain
`test`); they never connect to Supabase.

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (expects the API at http://localhost:8000)
npm run build
npm run lint
```

Set `VITE_API_BASE_URL` in `frontend/.env.local` if the API runs elsewhere.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/applications` | Directory cards (published only) |
| GET | `/api/applications/{slug}` | A pre-built guide, or 404 |
| GET | `/api/guides/{public_id}` | An unlisted generated guide, or 404 |

Errors always look like `{"error": {"code": "...", "message": "..."}}`.

## Adding an application

Add `seed_data/guides/<slug>.json` (same shape as the existing files) and run
`python -m scripts.seed_applications`. No frontend code or migration is needed.

## Not built yet

- The research form validates input but does not send anything (Phase 3).
- Deployment configuration (Phase 4).
