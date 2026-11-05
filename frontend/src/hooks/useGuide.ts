// Loads one guide by ID (a slug or a public ID) and reports its state.
// Shared by the pre-built and generated guide pages.

import { useEffect, useState } from 'react'
import type { GuideContent } from '@/types/guide'

export type GuideLoadState =
  | { kind: 'loading' }
  | { kind: 'not-found' }
  | { kind: 'error' }
  | { kind: 'loaded'; guide: GuideContent }

export function useGuide(id: string, load: (id: string) => Promise<GuideContent | null>) {
  // `attempt` increases on retry. A stored result counts only if it belongs
  // to the current id AND attempt; otherwise we report "loading" without an
  // extra setState call.
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ key: string; state: GuideLoadState } | null>(null)
  const key = `${id}#${attempt}`

  useEffect(() => {
    let cancelled = false // ignore late results after the id changes or the page unmounts
    load(id)
      .then((guide) => {
        if (!cancelled) setResult({ key, state: guide ? { kind: 'loaded', guide } : { kind: 'not-found' } })
      })
      .catch(() => {
        if (!cancelled) setResult({ key, state: { kind: 'error' } })
      })
    return () => {
      cancelled = true
    }
  }, [id, load, key])

  const state: GuideLoadState = result?.key === key ? result.state : { kind: 'loading' }
  return { state, retry: () => setAttempt((n) => n + 1) }
}
