import { Checkbox } from '@/components/ui/checkbox'
import { useChecklist } from '@/hooks/useChecklist'
import type { ChecklistItem } from '@/types/guide'
import { EmptyNote, GuideSection, SourceRefs } from './GuideParts'

interface GuideChecklistProps {
  guideKey: string
  items: ChecklistItem[]
}

export function GuideChecklist({ guideKey, items }: GuideChecklistProps) {
  const checklist = useChecklist(
    guideKey,
    items.map((item) => item.id),
  )

  return (
    <GuideSection id="checklist" title="Completion checklist">
      <p className="text-xs text-muted-foreground">
        {checklist.completedCount} of {items.length} done · Saved only in this browser; not shared with anyone else.
      </p>
      {items.length === 0 ? (
        <EmptyNote />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => {
            const inputId = `check-${item.id}`
            const checked = checklist.isChecked(item.id)
            return (
              <li key={item.id} className="flex items-start gap-3">
                <Checkbox id={inputId} checked={checked} onCheckedChange={() => checklist.toggle(item.id)} className="mt-0.5" />
                {/* htmlFor links the label to the checkbox, so clicking the text toggles it too. */}
                <label htmlFor={inputId} className={checked ? 'text-muted-foreground line-through' : ''}>
                  {item.label}
                  <SourceRefs ids={item.source_ids} />
                </label>
              </li>
            )
          })}
        </ul>
      )}
    </GuideSection>
  )
}
