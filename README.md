# OAuth Setup Guides (working title)

A research and guide tool that helps developers understand the work involved
in setting up OAuth with third-party providers. See `PROJECT_SPEC.md`.

> Status: **Phase 1 of 4**: frontend only. The full README (architecture,
> environment variables, migrations, deployment) arrives in Phase 4.

## Repository layout

```text
frontend/            React + TypeScript + Vite + Tailwind + shadcn/ui
seed_data/guides/    The six researched guides (one JSON file per application)
PROJECT_SPEC.md      Product specification
CLAUDE_CODE_PROMPT.md  Implementation instructions
DECISIONS.md         Decision / assumption log
```

## Run the frontend locally

Requires Node.js 20.19+ or 22.12+ (developed on Node 26 LTS).

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
npm run lint
```

## What is temporary in Phase 1

- Guides are read straight from `seed_data/guides/*.json` at build time
  (`frontend/src/services/guideService.ts`). Phase 2 swaps this for API calls.
- The research form validates input but does not send anything; the
  research agent is built in Phase 3.
- `/guides/:publicId` (generated guides) always shows "Not found" until
  the backend exists.
