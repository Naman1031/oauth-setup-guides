// Returns true once `active` has been true for `afterMs`.
// Used ONLY to explain a wait ("the server may be waking up"), never to fake
// progress: no stage or result depends on this timer.

import { useEffect, useState } from 'react'

export function useSlowHint(active: boolean, afterMs = 4000): boolean {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!active) return
    const timer = window.setTimeout(() => setSlow(true), afterMs)
    return () => {
      window.clearTimeout(timer)
      setSlow(false)
    }
  }, [active, afterMs])
  return active && slow
}
