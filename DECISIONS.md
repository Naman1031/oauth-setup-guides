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
