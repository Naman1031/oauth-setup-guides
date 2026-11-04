import type { ReactNode } from 'react'
import { Link } from 'react-router'

/** Neutral working title only: the spec asks for no product name or branding. */
export const WORKING_TITLE = 'OAuth Setup Guides'

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-svh bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center px-4 sm:px-6">
          <Link to="/" className="font-semibold tracking-tight">
            {WORKING_TITLE}
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
      <footer className="mx-auto max-w-5xl px-4 pb-10 text-xs text-muted-foreground sm:px-6">
        Guides are research aids based on public documentation. They are not proof that a provider will approve your app.
      </footer>
    </div>
  )
}
