import { Check, Circle, Loader2, RotateCcw, X } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { STAGES, type ResearchState, type StageState } from '@/hooks/useResearch'
import { cn } from '@/lib/utils'

const stateText: Record<StageState, string> = {
  pending: 'Waiting',
  started: 'In progress',
  completed: 'Done',
  failed: 'Failed',
}

function StageIcon({ state }: { state: StageState }) {
  if (state === 'completed') return <Check className="size-4 text-emerald-600" />
  if (state === 'failed') return <X className="size-4 text-destructive" />
  // The spinner only appears after the backend reported this stage "started".
  if (state === 'started') return <Loader2 className="size-4 animate-spin text-primary" />
  return <Circle className="size-4 text-muted-foreground/50" />
}

interface ResearchProgressProps {
  applicationName: string
  state: ResearchState
  onRetry: () => void
  onEdit: () => void
}

export function ResearchProgress({ applicationName, state, onRetry, onEdit }: ResearchProgressProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm">
        Researching <span className="font-medium">{applicationName}</span>. This usually takes one to a few minutes.
      </p>

      <ol className="space-y-2" aria-live="polite">
        {STAGES.map((stage) => {
          const stageState = state.stages[stage.key]
          return (
            <li key={stage.key} className="flex items-center gap-3 text-sm">
              <StageIcon state={stageState} />
              <span className={cn(stageState === 'pending' && 'text-muted-foreground')}>{stage.label}</span>
              <span className="sr-only">: {stateText[stageState]}</span>
              {stage.key === 'searching_documentation' && state.webSearches > 0 && (
                <span className="text-xs text-muted-foreground">
                  {state.webSearches} web {state.webSearches === 1 ? 'search' : 'searches'} completed
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {state.status === 'failed' && state.error && (
        <Alert variant="destructive">
          <X />
          <AlertTitle>Research did not complete</AlertTitle>
          <AlertDescription>
            <p>{state.error.message} No guide was saved.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {state.error.retryable && (
                <Button size="sm" onClick={onRetry}>
                  <RotateCcw /> Try again
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={onEdit}>
                Edit input
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
