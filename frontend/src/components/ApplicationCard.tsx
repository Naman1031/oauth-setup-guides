import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { complexityLabels } from '@/lib/guideLabels'
import type { ApplicationSummary, Complexity } from '@/types/guide'

const complexityStyles: Record<Complexity, string> = {
  easy: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  complex: 'border-rose-200 bg-rose-50 text-rose-800',
}

export function ApplicationCard({ app }: { app: ApplicationSummary }) {
  return (
    // The whole card is one link, so it is easy to tap on mobile.
    <Link to={`/apps/${app.slug}`} className="group block rounded-xl focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none">
      <Card className="h-full transition-colors group-hover:border-primary/40">
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle>{app.name}</CardTitle>
            <Badge variant="outline" className={complexityStyles[app.complexity]}>
              {complexityLabels[app.complexity]}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">{app.category}</p>
          <CardDescription className="mt-1">{app.short_description}</CardDescription>
          <span className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary">
            View guide <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </CardHeader>
      </Card>
    </Link>
  )
}
