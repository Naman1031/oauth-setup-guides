# OAuth Setup Guides (working title)

A small web application that helps developers understand the work involved in
setting up OAuth for a third-party application **before** they integrate it.
It is a research and guide product, not an OAuth provider or credential manager.

- **Directory** of six hand-researched guides: GitHub, Slack, Google Drive, Notion, HubSpot, Discord.
- **Research agent:** enter any application name; one OpenAI Responses API call with the
  built-in `web_search` tool researches it, streaming real progress to the browser, and
  saves a validated, source-backed guide under an unlisted URL.
- Every guide uses **one schema and one layout**: ten sections plus a completion checklist,
  separate active-effort vs. provider-review time, Verified / Estimated / Unknown evidence
  labels, an agent-vs-human task split with a portal-exploration record, and Composio
  Managed OAuth availability.
- **Copy Guide** (Markdown with sources), **Share Guide** (copies the URL), and a checklist
  stored only in your browser.

| Deliverable | Link |
|---|---|
| **Live application** | https://oauth-setup-guides-azure.vercel.app |
| **API** (health) | https://oauth-guides-api-sxqs.onrender.com/api/health |
| **Source repository** | https://github.com/Naman1031/oauth-setup-guides |

Example generated guides (unlisted links):
[Linear, OAuth supported](https://oauth-setup-guides-azure.vercel.app/guides/CwJRgSWgZWtlL7d1dqMDG4sWVsVB4E-Ap69LFwoGdog) ·
[Craigslist, OAuth not supported](https://oauth-setup-guides-azure.vercel.app/guides/Nn5iUlPITmpdGeM2vAkC2fX9fSJrgKWXkohmZARwzgk)

> The API runs on Render's free plan and sleeps after 15 idle minutes, so the first
> page load can take up to a minute while it wakes up.

Specification: [`PROJECT_SPEC.md`](PROJECT_SPEC.md) · Decisions: [`DECISIONS.md`](DECISIONS.md) · Test report: [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)

---

## Architecture

```text
Browser ── React + TypeScript (Vite, Tailwind, shadcn/ui)            Vercel
   │  fetch JSON  /  fetch POST + Server-Sent Events
   ▼
FastAPI (Pydantic, SQLAlchemy, Alembic)                              Render
   │  routes → services → models          └── research workflow ──▶ OpenAI Responses API
   ▼                                                                   + built-in web_search
PostgreSQL                                                           Supabase
   applications (6 published guides)   generated_guides (unlisted results)
```

The frontend never talks to the database or to OpenAI. All secrets live in backend
environment variables.

```text
frontend/
  src/types/guide.ts              shared guide schema (TypeScript mirror)
  src/services/                   the only code that calls the API (guides + research SSE)
  src/components/guide/           GuideView: renders ANY guide from data
  src/pages/, src/hooks/          routes, loading/checklist/research state
  vercel.json                     SPA rewrite + security headers
backend/
  app/schemas/guide.py            GuideContent: THE shared schema (+ cross-checks)
  app/models/                     the two tables
  app/services/                   all database queries; research/ = the agent
  app/api/                        thin HTTP routes, one error shape
  migrations/                     Alembic (0001 creates both tables + RLS)
  scripts/                        seed_applications, create_test_database, e2e_check
  tests/                          151 pytest tests (fake OpenAI client: no cost)
seed_data/guides/<slug>.json      one file per directory application
render.yaml                       Render Blueprint for the API
```

### How a research request works

```text
POST /api/research/stream {application_name, website_url?}
 1 validating_input        Pydantic + URL safety (http/https only; no credentials,
                           localhost, private/reserved IPs). The URL is never fetched by us.
 2 searching_documentation ONE client.responses.stream(...) call: web_search tool,
                           tool_choice="required", max_tool_calls, max_output_tokens,
                           strict JSON schema, store=False, no SDK retries
 3 analysing_requirements  from the first streamed output token until the response completes
 4 validating_guide        JSON → full GuideContent validation → evidence reconciliation
 5 saving_result           insert with a random 43-character public_id
 → event: complete {guide_path}   or   event: error {code, message, retryable}
```

Each stage event is sent when that work actually starts or finishes. There are no timers.

**Evidence reconciliation** ([`evidence.py`](backend/app/services/research/evidence.py)):
the API separately reports the searches the model ran, the pages it opened and the URLs it
consulted. Sources the model lists but that never appeared in that report are removed, and
any "Verified" claim left without a source becomes "Unknown". Portal pages count as
"inspected" only if they were really opened, and the "safe actions attempted" list is
generated from the real action log. Dates, domains and "Not tested" are set by the backend.
A result is saved only if it validates and keeps at least one confirmed source.

**Safety boundary:** the agent uses public, signed-out pages only. It never logs in,
creates apps, accepts terms, submits forms or handles credentials, and every guide says
exactly what the human must do next.

---

## Local setup

Requirements: Python 3.12, Node.js 20.19+ or 22.12+ (developed on Node 26 LTS), a
Supabase project (or any PostgreSQL 15+), and a local PostgreSQL for tests.

### 1. Backend

```bash
cd backend
py -3.12 -m venv .venv                 # macOS/Linux: python3.12 -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env                 # macOS/Linux: cp .env.example .env, then edit it
alembic upgrade head                   # create tables in DATABASE_URL
python -m scripts.seed_applications    # load the six guides (safe to re-run; --dry-run validates only)
uvicorn app.main:app --reload          # http://localhost:8000/api/health, docs at /docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (expects the API at http://localhost:8000)
```

To point it elsewhere, create `frontend/.env.local` with `VITE_API_BASE_URL=...`.

### 3. Tests

```bash
cd backend
python -m scripts.create_test_database     # once; creates the DB named in TEST_DATABASE_URL
pytest                                     # 151 tests, no OpenAI cost (fake client)
python -m scripts.e2e_check --api http://localhost:8000 --frontend-origin http://localhost:5173

cd ../frontend
npm run build && npm run lint
```

The test suite only ever connects to `TEST_DATABASE_URL`, and refuses database names
that don't contain `test`. It never touches Supabase.

---

## Environment variables

**Backend** (`backend/.env` locally; Render dashboard in production). Template: [`backend/.env.example`](backend/.env.example).

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Supabase **session pooler** URI (`postgresql://...pooler.supabase.com:5432/postgres`) |
| `CORS_ORIGINS` | prod | Comma-separated frontend origins; must be `https://` in production; `*` is refused |
| `ENVIRONMENT` | prod | `production` disables `/docs` and enforces https CORS |
| `OPENAI_API_KEY` | for research | Secret API key (billed separately from ChatGPT) |
| `OPENAI_MODEL` | for research | e.g. `gpt-6-luna` (needs Responses + web_search + Structured Outputs) |
| `OPENAI_REASONING_EFFORT` | no | `medium` (default) |
| `OPENAI_SEARCH_CONTEXT_SIZE` | no | `medium` (default) |
| `OPENAI_MAX_TOOL_CALLS` | no | Max web searches per request, default `8` |
| `OPENAI_MAX_OUTPUT_TOKENS` | no | Includes reasoning tokens, default `20000` |
| `OPENAI_TIMEOUT_SECONDS` | no | Default `300` |
| `RESEARCH_REQUESTS_PER_IP_PER_HOUR` | no | Default `5` |
| `RESEARCH_REQUESTS_PER_DAY` | no | Whole server, default `30` |
| `RESEARCH_MAX_CONCURRENT` | no | Default `2` |
| `TEST_DATABASE_URL` | tests | Local PostgreSQL database whose name contains `test` |

**Frontend** (`frontend/.env.local`; Vercel project settings). Everything here is **public**.

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | API origin, e.g. `https://oauth-guides-api.onrender.com` |

---

## Database: migrations and seeding

- Two tables only: `applications` and `generated_guides`. Relational metadata lives in
  columns; the guide itself is one JSONB document validated by `GuideContent`.
- `alembic upgrade head` applies [`0001`](backend/migrations/versions/0001_create_applications_and_generated_guides.py):
  tables, unique indexes (`slug`, `public_id`), the `is_published` index, a `result_type`
  check constraint, and **Row Level Security with no policies**. Supabase exposes `public`
  tables through its Data API, and this blocks that API completely. The backend connects
  as the table owner and is unaffected.
- `python -m scripts.seed_applications` validates **every** seed file first and then
  upserts all of them in one transaction (nothing is written if any file is invalid).

### Adding application #7 (and scaling to 100+)

1. Create `seed_data/guides/<slug>.json` with `slug`, `name`, `category`,
   `short_description` and a `guide_content` that follows the schema.
2. Run `python -m scripts.seed_applications --dry-run`, then without `--dry-run`.

No frontend code and no migration is needed: the directory, search and guide page are
data-driven, and nothing in the UI branches on a provider name. The schema already expresses
the differences between providers (conditional scopes, several kinds of approval, unknown
wait times, missing Composio support). At 100+ entries the remaining work is product-side:
server-side search/pagination for `GET /api/applications` (a query parameter plus an index
on `name`), and re-researching guides as `last_researched_at` ages.

---

## Deployment (Supabase + Render + Vercel, all free tiers)

1. **Supabase:** create a project. Copy the **Session pooler** connection string (the direct
   connection is IPv6-only). From your machine, with `DATABASE_URL` pointing at it, run
   `alembic upgrade head` and `python -m scripts.seed_applications`. Migrations are run from
   your machine because Render's `preDeployCommand` is a paid feature.
2. **GitHub:** push this repository.
3. **Render:** New → Blueprint → select the repo. [`render.yaml`](render.yaml) creates a free
   Python web service from `backend/`. It asks for `DATABASE_URL`, `CORS_ORIGINS` and
   `OPENAI_API_KEY`; enter a placeholder for `CORS_ORIGINS` until the Vercel URL exists.
   Health check: `/api/health`.
4. **Vercel:** import the repo, set **Root Directory = `frontend`** (framework preset: Vite),
   and add `VITE_API_BASE_URL` = your Render URL. [`frontend/vercel.json`](frontend/vercel.json)
   provides the SPA rewrite and security headers.
5. Set Render's `CORS_ORIGINS` to the Vercel URL (e.g. `https://your-app.vercel.app`). Changing
   it restarts the service.
6. Verify: `python -m scripts.e2e_check --api <render-url> --frontend <vercel-url> --production`.
   The Content-Security-Policy allows API calls to `https://*.onrender.com`; if the API moves to
   another domain, update `connect-src` in `vercel.json`.

---

## Cost controls (OpenAI)

- One bounded Responses API call per research request; no automatic retries (`max_retries=0`).
- `max_tool_calls` (default 8) caps paid web searches ($10 per 1,000 calls) and
  `max_output_tokens` caps generation, including reasoning tokens.
- Rate limits: 5 per IP per hour, 30 per server per day, 2 concurrent. Invalid input is
  rejected before a rate-limit slot or an OpenAI call is used.
- Measured: one run (Linear, `gpt-6-luna`) used 3 searches, 24k input tokens and 5k output
  tokens, about **$0.035**.
- Set a **hard spend limit** in the OpenAI dashboard (Project settings → Limits →
  "Enforce a hard limit"). OpenAI documents that requests then fail with HTTP 429 (enforcement
  is not instantaneous), and spend *alerts* alone do not stop traffic. The app reports this
  as "usage limit reached" and does not retry.

## Security summary

Secrets only in backend env vars · strict input validation, URLs never fetched by the server
(no SSRF surface) · https-only CORS allow-list in production · parameterized ORM queries ·
one safe error shape (no stack traces or provider messages) · `X-Robots-Tag: noindex` and
`nosniff` on every API response · CSP, frame and referrer headers on the frontend · guide text
rendered as text (no HTML injection) and links restricted to http(s) · RLS on Supabase tables ·
no OAuth secrets or user credentials stored anywhere. Retrieved web content is treated as
untrusted, both in the prompt and by checking claims against the API's action log.

**Unlisted, not private:** anyone who has a generated guide's URL can open it. The URL is
unguessable (256 random bits), but it isn't access-controlled.

---

## Key decisions

**What "OAuth supported" means:** the developer can register an OAuth app so that *their end users* can connect their own accounts (delegated authorization with a consent screen). An application that only offers access to the developer's own account, such as Craigslist's Bulkpost API (an OAuth client-credentials token for your own posting account), API keys or personal tokens, is shown as **not supported**, with that alternative explained. This comes straight from the assignment's framing ("wants their users to connect an app").

See [`DECISIONS.md`](DECISIONS.md) for the full log. Highlights: one shared Pydantic schema
for seeded and generated guides; JSONB for guide content; the six seed guides researched by
hand from official docs (URLs verified 2026-11-04); a single streamed OpenAI call whose real
events drive the progress stages; trusting the API's action log over the model's prose;
in-process rate limiting (no Redis); no Docker, LangChain, auth or job queue.

## Known limitations

- **Portal exploration is shallow:** `web_search` can open public pages but cannot run
  JavaScript, click, or sign in. Most provider portals sit behind a login, so guides
  usually record "not accessible" or "not attempted", and say so.
- **Research depth varies:** `gpt-6-luna` is OpenAI's smallest current model, and results
  depend on what search finds. Generated guides are research aids, not proof that a
  provider will approve an app.
- **Rate limits are per process:** they reset when the server restarts and aren't shared
  between instances. Behind Render's proxy the client IP comes from `X-Forwarded-For`,
  which a client can influence, so the per-IP limit is best-effort; the daily and
  concurrency limits still cap total spend.
- **Free-tier hosting:** Render spins the API down after 15 minutes idle, and waking it takes
  about a minute (the UI explains the wait). Vercel Hobby is for personal, non-commercial use.
- Seed guides are not tested end to end against the providers (marked "Not tested"), and
  guides do not refresh automatically as provider docs change.
- The seed script never unpublishes an application whose file was deleted; set
  `is_published = false` instead.
