import { useEffect, useState } from 'react'
import JobPage from './pages/JobPage'
import UploadPage from './pages/UploadPage'

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const on = () => setHash(window.location.hash)
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash
}

export default function App() {
  const hash = useHashRoute()
  const jobMatch = hash.match(/^#\/job\/([0-9a-f-]{36})$/i)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="#/" className="text-xl font-bold text-gray-900">
            DrumScript
          </a>
          {jobMatch && (
            <a href="#/" className="text-sm text-primary-700 hover:underline" data-testid="new-upload">
              ← New upload
            </a>
          )}
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">{jobMatch ? <JobPage jobId={jobMatch[1]} /> : <UploadPage />}</main>
    </div>
  )
}
