// Checklist state that lives ONLY in this browser (localStorage).
// Nothing here is sent to the backend, so other viewers of the same
// guide never see your ticks.

import { useState } from 'react'

const STORAGE_PREFIX = 'oauth-guide-checklist:'

/** Read saved ticks; any problem (private mode, bad JSON) falls back to "nothing ticked". */
function loadCheckedIds(storageKey: string): string[] {
  try {
    const raw = window.localStorage.getItem(storageKey)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    // Stored data is untrusted too: keep only string entries.
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}

/**
 * @param guideKey  Unique per guide, e.g. "app:github" or "generated:<public_id>".
 * @param validIds  The guide's current checklist item IDs; stale saved IDs are ignored.
 */
export function useChecklist(guideKey: string, validIds: string[]) {
  const storageKey = STORAGE_PREFIX + guideKey

  // The function passed to useState runs once, on first render ("lazy initial state").
  // The component using this hook is rendered with `key={guideKey}`, so React
  // creates a fresh instance (and re-reads storage) when you switch guides.
  const [checkedIds, setCheckedIds] = useState<string[]>(() => loadCheckedIds(storageKey))

  function toggle(itemId: string) {
    setCheckedIds((previous) => {
      const next = previous.includes(itemId)
        ? previous.filter((id) => id !== itemId)
        : [...previous, itemId]
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next))
      } catch {
        // Storage can be full or blocked; the tick still works for this visit.
      }
      return next
    })
  }

  const validSet = new Set(validIds)
  const checked = new Set(checkedIds.filter((id) => validSet.has(id)))

  return {
    isChecked: (itemId: string) => checked.has(itemId),
    toggle,
    completedCount: checked.size,
  }
}
