import { useEffect, useRef, useState } from 'react'
import { listJobs, uploadFile, type Job } from '../api'

const ACCEPT = ['mp3', 'wav', 'm4a', 'flac']

export default function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listJobs().then(setJobs).catch(() => undefined)
  }, [])

  const start = async (file: File | undefined) => {
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
    if (!ACCEPT.includes(ext)) {
      setError(`Unsupported file type ".${ext}". Use ${ACCEPT.join(', ')}.`)
      return
    }
    setError(null)
    setProgress(0)
    try {
      const job = await uploadFile(file, setProgress)
      window.location.hash = `#/job/${job.id}`
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setProgress(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div
        className={`bg-white rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300'
        }`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          void start(e.dataTransfer.files[0])
        }}
        data-testid="dropzone"
      >
        <h2 className="text-lg font-medium text-gray-900">Upload a song</h2>
        <p className="mt-1 text-sm text-gray-600">MP3, WAV, M4A or FLAC, up to 100 MB and 12 minutes.</p>
        <input
          ref={input}
          type="file"
          accept=".mp3,.wav,.m4a,.flac,audio/*"
          className="hidden"
          data-testid="file-input"
          onChange={(e) => void start(e.target.files?.[0])}
        />
        {progress === null ? (
          <button
            className="mt-5 px-4 py-2 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
            onClick={() => input.current?.click()}
          >
            Choose a file
          </button>
        ) : (
          <div className="mt-5" data-testid="upload-progress">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-primary-600 transition-all" style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <p className="mt-2 text-sm text-gray-600">Uploading… {Math.round(progress * 100)}%</p>
          </div>
        )}
        <p className="mt-4 text-xs text-gray-500">or drop the file here</p>
        {error && (
          <p className="mt-4 text-sm text-red-700" data-testid="upload-error">
            {error}
          </p>
        )}
      </div>

      <p className="text-sm text-gray-600 text-center">
        The drums are isolated, transcribed and laid out on a bar grid. On a laptop CPU expect roughly half the
        song's length in processing time.
      </p>

      {jobs.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Recent transcriptions</h3>
          <ul className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {jobs.map((j) => (
              <li key={j.id}>
                <a href={`#/job/${j.id}`} className="flex items-center justify-between px-4 py-2 hover:bg-gray-50 text-sm">
                  <span className="truncate text-gray-900">{j.filename}</span>
                  <span
                    className={
                      j.status === 'completed' ? 'text-green-700' : j.status === 'error' ? 'text-red-700' : 'text-gray-500'
                    }
                  >
                    {j.status}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
