// Data access for guides.
//
// PHASE 1 (temporary): reads the six researched seed files directly from
// ../seed_data/guides/*.json at build time.
// PHASE 2: these same three functions will call the FastAPI backend with
// `fetch` (GET /api/applications, /api/applications/{slug},
// /api/guides/{public_id}). Pages and components call only these
// functions, so they will not need to change.

import type { ApplicationRecord, ApplicationSummary, GuideContent } from '@/types/guide'

// `import.meta.glob` is a Vite feature: it finds every matching file at
// build time and bundles it. `eager: true` loads them immediately rather
// than lazily; `import: 'default'` gives us the parsed JSON object.
const seedFiles = import.meta.glob<ApplicationRecord>('../../../seed_data/guides/*.json', {
  eager: true,
  import: 'default',
})

// Sort by name so the directory order is stable and not tied to filenames.
const applications: ApplicationRecord[] = Object.values(seedFiles).sort((a, b) =>
  a.name.localeCompare(b.name),
)

/** Directory cards: only the fields a card needs (mirrors GET /api/applications). */
export async function listApplications(): Promise<ApplicationSummary[]> {
  return applications.map((app) => ({
    slug: app.slug,
    name: app.name,
    category: app.category,
    short_description: app.short_description,
    complexity: app.guide_content.complexity,
  }))
}

/** Full pre-built guide, or null if the slug is unknown (the API will return 404). */
export async function getApplicationGuide(slug: string): Promise<GuideContent | null> {
  const app = applications.find((candidate) => candidate.slug === slug)
  return app ? app.guide_content : null
}

/**
 * Generated (AI-researched) guide by its unlisted public ID.
 * There are no generated guides until the backend exists (Phases 2–3),
 * so this always returns null for now.
 */
export async function getGeneratedGuide(publicId: string): Promise<GuideContent | null> {
  void publicId // unused until Phase 2
  return null
}
