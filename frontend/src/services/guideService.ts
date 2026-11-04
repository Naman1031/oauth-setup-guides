// Data access for guides: the ONLY frontend file that talks to the backend.
// Pages and components call these three functions and never use fetch directly.

import type { ApplicationSummary, GuideContent } from '@/types/guide'

// Vite exposes only variables prefixed with VITE_ to browser code, and anything
// here is PUBLIC (it ends up in the downloaded JavaScript). Never put secrets here.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

/** Thrown for network problems and unexpected responses; pages show an error state. */
export class ApiRequestError extends Error {}

/**
 * GET a JSON endpoint. Returns null for 404 (a normal "not found" answer)
 * and throws for everything else that isn't a success.
 */
async function getJson<T>(path: string): Promise<T | null> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiRequestError('Could not reach the server.')
  }
  if (response.status === 404) return null
  if (!response.ok) throw new ApiRequestError(`Request failed (${response.status}).`)
  return (await response.json()) as T
}

/** Directory cards: GET /api/applications */
export async function listApplications(): Promise<ApplicationSummary[]> {
  return (await getJson<ApplicationSummary[]>('/api/applications')) ?? []
}

/** Full pre-built guide: GET /api/applications/{slug} → null if unknown/unpublished. */
export async function getApplicationGuide(slug: string): Promise<GuideContent | null> {
  // encodeURIComponent stops a crafted slug from changing the request path.
  const body = await getJson<{ guide_content: GuideContent }>(`/api/applications/${encodeURIComponent(slug)}`)
  return body ? body.guide_content : null
}

/** Unlisted generated guide: GET /api/guides/{public_id} → null if unknown. */
export async function getGeneratedGuide(publicId: string): Promise<GuideContent | null> {
  const body = await getJson<{ guide_content: GuideContent }>(`/api/guides/${encodeURIComponent(publicId)}`)
  return body ? body.guide_content : null
}
