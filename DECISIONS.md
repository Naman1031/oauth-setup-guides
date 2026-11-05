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
| 2026-11-05 | Research model **gpt-6-luna** (user's choice), configurable via `OPENAI_MODEL`; no default in code. | Cheapest current model listing Responses + web_search + Structured Outputs + streaming. First live run cost ≈ $0.035. |
| 2026-11-05 | One streamed `client.responses.stream(...)` call: `tool_choice="required"`, `max_tool_calls=8`, `max_output_tokens=20000`, `reasoning.effort=medium`, `search_context_size=medium`, `store=False`, SDK `max_retries=0`. | Spec cost controls: forced search, bounded calls/tokens, no automatic retries. |
| 2026-11-05 | Stage mapping: *searching* = request sent → first `response.output_text.delta`; *analysing* = first delta → `response.completed`. Search count comes from `response.web_search_call.completed`. | Every progress event corresponds to a real backend/stream event. |
| 2026-11-05 | Model-facing JSON Schema = `to_strict_json_schema(GuideContent)` minus `minLength`/`maxLength`; the reply is validated against the full `GuideContent`. | Docs don't list string-length keywords for strict mode; one shared schema stays the source of truth. |
| 2026-11-05 | Evidence reconciliation: sources must appear in `web_search_call.action.sources` / opened pages / citations; uncited Verified claims → Unknown; portal pages must have been opened; safe-actions list generated from the real action log; dates/domains/tested status set by the backend. | Spec: preserve real source URLs, never claim exploration that didn't happen. |
| 2026-11-05 | A result is saved only if it validates, keeps ≥1 confirmed source, and (if "supported") has ≥1 setup step. | Spec: never store empty/invalid results. |
| 2026-11-05 | In-process rate limits: 5/hour per IP, 30/day per server, 2 concurrent. Reset on restart; not shared across instances. | Spec allows an in-process limiter if documented. |
| 2026-11-05 | Frontend reads SSE from a `fetch` POST body (not `EventSource`, which is GET-only). A stream that ends without `complete`/`error` is shown as an error. | Spec: disconnects must never look like success. |
| 2026-11-05 | Research input is validated in the route BEFORE taking a rate-limit slot (422 on bad input); stage 1 re-validates. | Typos must not use up a user's hourly quota or cost anything. |
| 2026-11-05 | Security headers via a pure ASGI middleware (outermost) + explicitly on the 500 handler. | `@app.middleware` can't reach Starlette's crash responses; ASGI middleware doesn't buffer SSE. |
| 2026-11-05 | In production, `CORS_ORIGINS` must be https:// (startup fails otherwise). | Misconfiguration should fail loudly, not silently. |
| 2026-11-05 | `shadcn` moved to devDependencies. | It's a build-time CLI (one CSS import); its audit advisories don't ship to browsers. |
| 2026-11-05 | Migrations run manually from a developer machine, not on Render. | Render `preDeployCommand` is paid-only; avoids migrating during builds. |
| 2026-11-05 | Render: `--proxy-headers --forwarded-allow-ips="*"`; PYTHON_VERSION 3.12.2; region singapore. | Real client IP for rate limiting (best-effort, X-Forwarded-For is client-influenced); version parity with local; same region as Supabase. |
| 2026-11-05 | Vercel CSP allows `connect-src https://*.onrender.com`; `style-src 'unsafe-inline'`. | Built bundle has no inline scripts but React Router/Radix set inline style attributes. |
| 2026-11-05 | `robots.txt` does not Disallow `/guides/`. | Crawlers must fetch a page to see its noindex; Disallow would hide it. |
| 2026-11-05 | "Server may be waking up" hint after 4 s of loading. | Explains free-tier cold starts; it is not progress and no state depends on it. |
| 2026-11-05 | `.gitattributes` forces LF line endings. | Stops CRLF churn between Windows and Linux (Render/Vercel). |
| 2026-11-05 | **"OAuth supported" means delegated end-user authorization** (developer registers an OAuth app; each end user consents). Own-account-only access (OAuth client_credentials with the owner's credentials, API keys, personal tokens) is "not supported", with the alternative explained in the summary. | Decided from the original assignment ("wants their users to connect an app", "create an OAuth app … get it approved", "their users' connections"). Found via the Craigslist live run, which was labelled "supported" for its own-account Bulkpost API. |
| 2026-11-05 | `get_settings()` re-raises configuration errors with field names and reasons only (`ConfigurationError`, `from None`). | Pydantic's default message includes submitted values, which would leak the database URL / API key into Render logs on a failed start. |
