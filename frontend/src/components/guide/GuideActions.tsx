import type { ReactElement } from 'react'
import { Check, Copy, Link2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard'
import { guideToMarkdown } from '@/lib/guideMarkdown'
import type { GuideContent } from '@/types/guide'

interface GuideActionsProps {
  guide: GuideContent
  shareUrl: string
}

/** "Share Guide" copies the URL; "Copy Guide" copies the full guide as Markdown. */
export function GuideActions({ guide, shareUrl }: GuideActionsProps) {
  const share = useCopyToClipboard()
  const copyGuide = useCopyToClipboard()

  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="outline" onClick={() => share.copy(shareUrl)}>
        <StatusIcon status={share.status} idleIcon={<Link2 />} />
        {share.status === 'copied' ? 'Link copied' : share.status === 'failed' ? 'Copy failed' : 'Share Guide'}
      </Button>
      <Button onClick={() => copyGuide.copy(guideToMarkdown(guide, shareUrl))}>
        <StatusIcon status={copyGuide.status} idleIcon={<Copy />} />
        {copyGuide.status === 'copied' ? 'Guide copied' : copyGuide.status === 'failed' ? 'Copy failed' : 'Copy Guide'}
      </Button>
      {/* aria-live makes screen readers announce the copy result. */}
      <span className="sr-only" aria-live="polite">
        {share.status === 'copied' && 'Guide link copied to clipboard.'}
        {copyGuide.status === 'copied' && 'Guide copied to clipboard as Markdown.'}
        {(share.status === 'failed' || copyGuide.status === 'failed') && 'Copy to clipboard failed.'}
      </span>
    </div>
  )
}

function StatusIcon({ status, idleIcon }: { status: 'idle' | 'copied' | 'failed'; idleIcon: ReactElement }) {
  if (status === 'copied') return <Check />
  if (status === 'failed') return <X />
  return idleIcon
}
