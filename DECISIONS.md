# Decision and assumption log

Short record of implementation choices. Product and architecture decisions
belong to the project owner; anything here that changes behaviour was agreed
first.

| Date | Decision | Why |
|------|----------|-----|
| 2026-11-04 | Node.js 26 LTS (installed via winget). | The machine had Node 21, which current Vite does not support. |
| 2026-11-04 | The six guides were researched for real in Phase 1 and stored as `seed_data/guides/<slug>.json`. | Avoids throwaway placeholder facts. Phase 1 frontend reads these files; the Phase 2 seed script will load the same files into Supabase. |
| 2026-11-04 | Each seed file = one `applications` row: `slug`, `name`, `category`, `short_description` at top level, guide sections in `guide_content`. | Mirrors the agreed table design; adding app #7 means adding one JSON file. |
| 2026-11-04 | Portal exploration is shown as a subsection of section 7 (Agent vs. human tasks). | Keeps the spec's ten numbered sections. |
| 2026-11-04 | Research progress (Phase 3) will map real Responses-API stream events to the five UI stages, using one model call. | Genuine stages without doubling cost. |
| 2026-11-04 | Sources are stored once per guide with an `id`; other items reference them via `source_ids`. | No repeated URLs; lets validation check every citation resolves. |
| 2026-11-04 | `evidence_notes[].verification_basis` (`documentation` / `test`) is set only for Verified claims. | Spec requires saying whether Verified is documentation- or test-based. |
| 2026-11-04 | Seed-guide portal exploration = plain signed-out HTTP GETs (no JavaScript, no login). Recorded honestly: 5 of 6 portals not accessible, HubSpot partially explored. | Matches the safe-exploration boundary; no browser automation added. |
| 2026-11-04 | HubSpot guide targets the projects/CLI developer platform. | HubSpot disabled legacy public app creation for all accounts on 2026-06-23. |
| 2026-11-04 | Discord's conflicting review thresholds (10,000 users vs. 100 servers) are both shown, with the older claim marked Unknown. | Spec: if sources conflict, say so. |
| 2026-11-04 | Removed shadcn's `sonner` toast and `next-themes`; copy feedback is shown on the button itself. | Fewer dependencies; light theme only. |
| 2026-11-04 | Client-side research-form validation rejects IPv6 literals outright. | Simple and safe; the backend (Phase 3) does the authoritative check. |
| 2026-11-04 | Working title "OAuth Setup Guides". | Spec forbids inventing a product name. |
| 2026-11-05 | Tests run against a local PostgreSQL 18 database `oauth_guides_test`; production data lives in Supabase. | Real Postgres is needed for JSONB/constraints; tests never touch Supabase (conftest refuses DB names without "test"). |
| 2026-11-05 | `pydantic-settings` reads configuration from environment variables / `backend/.env`. | Standard FastAPI pattern; part of the Pydantic project. |
| 2026-11-05 | Driver: `psycopg` 3. Supabase `postgresql://` URLs are rewritten to `postgresql+psycopg://` automatically. | Lets users paste Supabase's URL unchanged. |
| 2026-11-05 | Supabase **session pooler** connection string (port 5432). | Direct connection is IPv6-only; Render needs IPv4. Session mode supports prepared statements. |
| 2026-11-05 | Row Level Security enabled (no policies) on both tables in migration 0001. | Supabase auto-exposes `public` tables via its Data API; verified the `anon` role sees 0 rows. Backend connects as owner, so it is unaffected. |
| 2026-11-05 | Migration 0001 is hand-written; `alembic check` confirms it matches the models. | Readable for learning; still verified mechanically. |
| 2026-11-05 | URLs are validated as http(s) with Pydantic's `HttpUrl` but stored as the original string. | `HttpUrl` normalizes (e.g. adds trailing slashes); the spec says to preserve exact source URLs. |
| 2026-11-05 | Public IDs: `secrets.token_urlsafe(32)` (43 chars, 256 bits). Malformed IDs return 404 without a DB query. | Unguessable unlisted URLs; internal UUID never exposed. |
| 2026-11-05 | `X-Robots-Tag: noindex, nofollow` on every API response (middleware). | API JSON should never be indexed, including error responses. |
| 2026-11-05 | Seed script lives at `backend/scripts/seed_applications.py` (spec suggested repo-root `scripts/`). | Runs inside the backend package/venv with `python -m scripts.seed_applications`; seed data stays at repo root. |
| 2026-11-05 | Seeding upserts by slug and requires filename = slug; it does not unpublish apps whose file was removed. | Repeatable and safe; unpublishing is a deliberate manual `is_published = false`. |
| 2026-11-05 | Test client dependency `httpx2` (pydantic/httpx2, by the httpx author) instead of `httpx`. | Starlette 1.10 deprecates `httpx` for its TestClient. Dev-only. |
| 2026-11-05 | Frontend now reads from the API via `VITE_API_BASE_URL` (default `http://localhost:8000`). | Phase 2 replaces Phase 1's bundled JSON; only `guideService.ts` changed. |
