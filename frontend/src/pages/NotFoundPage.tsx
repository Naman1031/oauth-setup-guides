import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFoundPage({ message = 'This page does not exist.' }: { message?: string }) {
  return (
    <div className="space-y-4 py-12 text-center">
      <title>Not found</title>
      <h1 className="text-2xl font-semibold tracking-tight">Not found</h1>
      <p className="text-muted-foreground">{message}</p>
      <Button asChild variant="outline">
        <Link to="/">Back to all applications</Link>
      </Button>
    </div>
  )
}
