import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { ResearchProgress } from '@/components/ResearchProgress'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useResearch } from '@/hooks/useResearch'
import { MAX_APP_NAME_LENGTH, MAX_URL_LENGTH, validateResearchInput, type ResearchInputErrors } from '@/lib/researchInput'

export function ResearchForm() {
  // "Controlled inputs": React state is the single source of truth for each field.
  const [applicationName, setApplicationName] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [errors, setErrors] = useState<ResearchInputErrors>({})
  const research = useResearch()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault() // stop the browser's default full-page form submission
    const validationErrors = validateResearchInput(applicationName, websiteUrl)
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
    // The backend re-validates everything; this check is only for quick feedback.
    void research.start(applicationName, websiteUrl)
  }

  if (research.state.status !== 'idle') {
    return (
      <ResearchProgress
        applicationName={applicationName.trim()}
        state={research.state}
        onRetry={() => void research.start(applicationName, websiteUrl)}
        onEdit={research.reset}
      />
    )
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="application-name">Application name</Label>
          <Input
            id="application-name"
            value={applicationName}
            onChange={(event) => setApplicationName(event.target.value)}
            placeholder="e.g. Linear"
            maxLength={MAX_APP_NAME_LENGTH}
            aria-invalid={Boolean(errors.applicationName)}
            aria-describedby={errors.applicationName ? 'application-name-error' : undefined}
            required
          />
          {errors.applicationName && (
            <p id="application-name-error" className="text-xs text-destructive">
              {errors.applicationName}
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="website-url">
            Website URL <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="website-url"
            type="url"
            inputMode="url"
            value={websiteUrl}
            onChange={(event) => setWebsiteUrl(event.target.value)}
            placeholder="https://example.com"
            maxLength={MAX_URL_LENGTH}
            aria-invalid={Boolean(errors.websiteUrl)}
            aria-describedby={errors.websiteUrl ? 'website-url-error' : undefined}
          />
          {errors.websiteUrl && (
            <p id="website-url-error" className="text-xs text-destructive">
              {errors.websiteUrl}
            </p>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        The research agent only uses public information. It cannot log in, register an OAuth app, or handle credentials,
        and it will never ask for your client secret. The generated guide gets an unlisted link: anyone with the link can
        view it.
      </p>

      <Button type="submit">
        <Search /> Generate Guide
      </Button>
    </form>
  )
}
