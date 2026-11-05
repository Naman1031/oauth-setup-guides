import { RotateCcw } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useSlowHint } from '@/hooks/useSlowHint'

/** Shown while waiting for the API; explains free-tier cold starts if it takes a while. */
export function LoadingNote({ label }: { label: string }) {
  const slow = useSlowHint(true)
  return (
    <div className="space-y-1 text-sm text-muted-foreground" role="status">
      <p>{label}</p>
      {slow && (
        <p className="text-xs">
          Still loading. The server may be waking up after being idle (free hosting), which can take up to a minute.
        </p>
      )}
    </div>
  )
}

/** Grey placeholder cards with the same size as directory cards (no animation). */
export function CardSkeletons({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="h-40 rounded-xl border bg-muted/50" />
      ))}
    </div>
  )
}

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Couldn't load</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        <Button size="sm" variant="outline" className="mt-3" onClick={onRetry}>
          <RotateCcw /> Try again
        </Button>
      </AlertDescription>
    </Alert>
  )
}
