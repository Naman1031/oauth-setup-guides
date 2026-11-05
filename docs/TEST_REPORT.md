# Test report

Date: 2026-11-05 · Branch: `main` · Live: https://oauth-setup-guides-azure.vercel.app · Environment: Windows 11, Python 3.12.2,
Node 26.13, local PostgreSQL 18 (tests), Supabase PostgreSQL 17.11 (data).

Status key: **Pass** = run and observed passing · **Partial** = some evidence, gap noted ·
**Not yet** = not run, with the reason.

## Automated suites (all run on 2026-11-05)

| Suite | Command | Result |
|---|---|---|
| Backend unit/integration (real PostgreSQL, fake OpenAI) | `cd backend && pytest` | **151 passed** |
| Migration ↔ models | `alembic check` | No new upgrade operations detected |
| **End-to-end, LIVE deployment** (Vercel + Render + Supabase) | `python -m scripts.e2e_check --api https://oauth-guides-api-sxqs.onrender.com --frontend https://oauth-setup-guides-azure.vercel.app --guide-id <id> --production` | **33/33 passed** |
| Clean install (fresh venv from requirements files only) | `pip install -r requirements-dev.txt && pytest` | 150/150 passed |
| Production mode locally (Render start command, `ENVIRONMENT=production`) | e2e check `--production` | 29/29 passed |
| End-to-end, local stack (API → Supabase) | `python -m scripts.e2e_check --api http://localhost:8000 --frontend-origin http://localhost:5173 --guide-id <id>` | **28/28 passed** |
| Frontend type-check + build | `npm run build` | Pass |
| Frontend lint | `npm run lint` | Pass (2 warnings inside generated shadcn `button`/`badge` files) |
| Frontend render smoke (all 6 guides, 11 sections in order, citations resolve, Copy Guide Markdown) | dev script via Vite SSR | 49/49 passed |
| Frontend SSE parser (7-byte chunks, split UTF-8, 429, dropped stream, network failure) | dev script | 4/4 passed |
| Dependency audit, backend runtime | `pip-audit -r requirements.txt` | No known vulnerabilities |
| Dependency audit, frontend runtime | `npm audit --omit=dev` | 0 vulnerabilities |
| Secret scan of all publishable files | grep for key/password patterns | None found (`.env` is git-ignored) |
| Seed-guide source URLs | HTTP check of all 60 cited URLs | 60/60 HTTP 200 (2026-11-04) |

`npm audit` including dev dependencies reports 6 low/moderate advisories, all inside the
`shadcn` CLI (`deepmerge`, `minimatch`, `ts-morph`). It is a dev-only build tool; none of its
code is in the shipped bundle (verified by searching `dist/assets/*.js`).

## Live OpenAI runs

| Run | Result | Usage / cost |
|---|---|---|
| Linear (`https://linear.app`), gpt-6-luna | Supported guide saved; all 5 stages streamed; 6/6 cited URLs return 200; 1 unconfirmable source dropped; portal claim downgraded to "not attempted" (no page opened) | 3 searches, 24,436 input / 5,143 output tokens (1,569 reasoning), 56.6 s, **≈ $0.035** |
| Craigslist (`https://www.craigslist.org`), gpt-6-luna, run by the user from the UI | Guide saved; all 4 sources confirmed. **Fact-checked 9/9 claims against Craigslist's pages** (case-by-case access, eligible categories, phone 415-399-5200 x8283, token URL, `email;accountID:password` Basic auth, scopes, 3600 s token, block credit). **Problem found:** labelled "OAuth supported" because Craigslist documents an OAuth *client_credentials* grant, which only gives access to the poster's own account, with no app registration and no end-user consent. **Fixed in the prompt** (see DECISIONS.md, 2026-11-05); the stored guide is left unchanged | 4 search calls (11 queries), 32,709 input / 4,729 output tokens, 60.3 s, **≈ $0.046** |
| Craigslist again, **after the prompt fix** (locally, then on the live site) | Both saved as **OAuth not supported**; summary explains the own-account Bulkpost `client_credentials` alternative. The live-site run also confirmed Render streams the SSE progress end to end | ≈ $0.05 each |

## Acceptance criteria (spec §13)

### Directory and guides
| Criterion | Status | Evidence |
|---|---|---|
| Home shows all six apps | Pass | e2e check; render smoke |
| Search finds each of the six | Pass | e2e check (name matching) + render smoke |
| Card opens the correct guide | Pass | checked by the user in a real browser (2026-11-05) |
| Same schema and layout for all six | Pass | schema tests; 11 sections in order for each |
| Sources, evidence labels, research date, tested status, Composio section | Pass | e2e check; schema tests |
| Approval/scope claims sourced and conditional | Pass | seed data checks (every conditional scope has a note; every citation resolves) |

### Research flow
| Criterion | Status | Evidence |
|---|---|---|
| Searches official docs; inspects public pages where possible | Pass | live run: 3 searches + page opens recorded |
| Records portal exploration status | Pass | reconciliation tests; live run downgraded honestly |
| Safe actions + human handoff recorded | Pass | generated from the real action log; handoff present |
| Never logs in / creates apps / submits forms | Pass (by design) | tool is search-only; prompt boundary; no browser automation |
| Supported app → structured guide | Pass | live Linear run |
| Unsupported app → honest result | Pass | Craigslist after the prompt fix: "OAuth not supported", confirmed by two live runs (one on the deployed site) |
| Insufficient evidence → inconclusive, not fabricated | Partial | tests: zero confirmed sources → not saved; unsourced Verified → Unknown; no live run |
| Progress reflects backend stages | Pass | stage-order test; live timings (search 0.3 s → 27.3 s) |
| Saved with unique share URL | Pass | random 43-char `public_id`; uniqueness test |
| Technical failure saves nothing | Pass | 12 failure-mode tests assert zero rows |
| Opens in a separate session by URL | Pass | GET `/api/guides/{id}` with no state (e2e) |
| Not in the directory | Pass | e2e check + API test |

### Guide interactions
| Criterion | Status | Evidence |
|---|---|---|
| Copy Guide copies content + source URLs | Pass | user-checked in a browser; Markdown generator verified for all 6 |
| Share Guide copies the exact URL | Pass | user-checked in a browser |
| Checklist persists after refresh | Pass | user-checked in a browser |
| Checklist not sent to the backend | Pass (by design) | no API endpoint accepts checklist data |
| Generated guide read-only | Pass (by design) | no write endpoints for guides |

### Security and reliability
| Criterion | Status | Evidence |
|---|---|---|
| OpenAI key never exposed to frontend | Pass | key only in backend settings (`SecretStr`); secret scan; error tests assert no `sk-` |
| Invalid schemes / malformed URLs rejected | Pass | 31 input tests; e2e (422) |
| Local / private addresses rejected | Pass | same |
| CORS restricted in production | Pass | allow/deny tests; https-only rule test |
| Research endpoint rate-limited | Pass | limiter tests; 429 + `Retry-After` test |
| Raw errors/secrets not shown | Pass | safe-500 tests; error-mapping tests |
| Guide content rendered safely | Pass | React text rendering; `safeHref` blocks `javascript:` |
| No credentials / OAuth secrets stored | Pass (by design) | schema forbids unknown fields; no such columns |

### Scalability and deployment
| Criterion | Status | Evidence |
|---|---|---|
| 7th app via data only | Pass (by design) | data-driven directory; seed tests load any `*.json` |
| Frontend deployable to Vercel | Pass | deployed: https://oauth-setup-guides-azure.vercel.app (SPA rewrite, CSP, noindex verified) |
| Backend deployable to Render | Pass | deployed via `render.yaml` Blueprint: https://oauth-guides-api-sxqs.onrender.com |
| Migrations + seed against Supabase | Pass | `alembic upgrade head` + seed run on 2026-11-05 |
| README + `.env.example` | Pass | this repository |
| Deployed URL, repo URL verified | Pass | live e2e 33/33; repo https://github.com/Naman1031/oauth-setup-guides matches local `main` |

## Verified after deployment
1. Render streams the ~60-second SSE progress without buffering (live Craigslist run from the deployed site).
2. Vercel sends `X-Robots-Tag: noindex` on rewritten `/guides/*` pages (e2e check).
3. The CSP doesn't block the app: guides load and research works in a real browser on the live site.
4. Browser checks by the user: layout incl. narrow width, search, checklist persistence, Share/Copy, citations.

## What checking the guidance taught us
- Seed guides: 60/60 cited URLs live; several were updated to the pages they now redirect to; HubSpot's guide was rebuilt for its new CLI platform (legacy app creation ended 2026-06-23); Discord's two conflicting review thresholds are both shown, the older one marked Unknown.
- Linear (live): 1 source the model listed was never seen by the search, so it was dropped; its claim of portal exploration was downgraded because no portal page was opened.
- Craigslist (live): every fact was right, but the *meaning* of "supported" was wrong for this product, which led to the definition now in the prompt.
