// Copies text to the clipboard and remembers the outcome briefly so a
// button can show "Copied" or "Copy failed".

import { useEffect, useRef, useState } from 'react'

type CopyStatus = 'idle' | 'copied' | 'failed'

export function useCopyToClipboard(resetAfterMs = 2000) {
  const [status, setStatus] = useState<CopyStatus>('idle')
  const timerRef = useRef<number | undefined>(undefined)

  // Clear any pending timer if the component unmounts.
  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  async function copy(text: string) {
    try {
      // The Clipboard API needs a secure context (https or localhost).
      await navigator.clipboard.writeText(text)
      setStatus('copied')
    } catch {
      setStatus('failed')
    }
    window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => setStatus('idle'), resetAfterMs)
  }

  return { status, copy }
}
