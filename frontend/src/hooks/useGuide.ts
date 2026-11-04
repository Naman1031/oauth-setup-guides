// Loads one guide by ID (a slug or a public ID) and reports its state.
// Shared by the pre-built and generated guide pages.

import { useEffect, useState } from 'react'
import type { GuideContent } from '@/types/guide'

export type GuideLoadState =
  | { kind: 'loading' }
  | { kind: 'not-found' }
  | { kind: 'error' }
  | { kind: 'loaded'; guide: GuideContent }

export function useGuide(id: string, load: (id: string) => Promise<GuideContent | null>): GuideLoadState {
  // Remember WHICH id a result belongs to. If the URL changes to a new id,
  // the stored result no longer matches and we report "loading" until the
  // new result arrives, without an extra setState call.
  const [result, setResult] = useState<{ id: string; state: GuideLoadState } | null>(null)

  useEffect(() => {
    let cancelled = false // ignore late results after the id changes or the page unmounts
    load(id)
      .then((guide) => {
        if (!cancelled) setResult({ id, state: guide ? { kind: 'loaded', guide } : { kind: 'not-found' } })
      })
      .catch(() => {
        if (!cancelled) setResult({ id, state: { kind: 'error' } })
      })
    return () => {
      cancelled = true
    }
  }, [id, load])

  return result?.id === id ? result.state : { kind: 'loading' }
}
