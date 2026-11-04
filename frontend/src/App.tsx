import { BrowserRouter, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/AppLayout'
import { ApplicationGuidePage } from '@/pages/ApplicationGuidePage'
import { GeneratedGuidePage } from '@/pages/GeneratedGuidePage'
import { HomePage } from '@/pages/HomePage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// URL → page mapping. React Router swaps pages without a full page reload.
export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/apps/:slug" element={<ApplicationGuidePage />} />
          <Route path="/guides/:publicId" element={<GeneratedGuidePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  )
}
