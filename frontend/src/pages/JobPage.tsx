import { useEffect, useState } from 'react'
import { getJob, getResult, type Job, type JobResult } from '../api'
import ChartView from '../components/ChartView'

const STAGES: Record<string, string> = {
  queued: 'Waiting for the worker…',
  decoding: 'Reading the audio…',
  separating_drums: 'Isolating the drums (Demucs) — the slow step…',
  transcribing: 'Detecting drum hits (ADTOF)…',
  tracking_beats: 'Finding beats and bar lines (Beat This!)…',
  writing_notation: 'Writing the chart…',
  done: 'Done',
}

export default function JobPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null)
  const [result, setResult] = useState<JobResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let timer = 0
    setJob(null)
    setResult(null)
    setError(null)
    const poll = async () => {
      try {
        const j = await getJob(jobId)
        if (cancelled) return
        setJob(j)
        if (j.status === 'completed') {
          const r = await getResult(jobId)
          if (!cancelled) setResult(r)
          return
        }
        if (j.status === 'error') return
        timer = window.setTimeout(poll, 1000)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [jobId])

  if (error) {
    return (
      <div className="max-w-xl mx-auto bg-red-50 border border-red-200 rounded-lg p-4 text-red-800" data-testid="job-error">
        {error}. <a className="underline" href="#/">Back to upload</a>
      </div>
    )
  }
  if (!job) return <p className="text-gray-500">Loading…</p>

  if (job.status === 'error') {
    return (
      <div className="max-w-xl mx-auto bg-red-50 border border-red-200 rounded-lg p-4" data-testid="job-error">
        <h2 className="font-medium text-red-800">Processing failed</h2>
        <p className="mt-1 text-sm text-red-700">{job.error_message || 'Unknown error'}</p>
        <a className="mt-3 inline-block text-sm underline text-red-800" href="#/">
          Try another file
        </a>
      </div>
    )
  }

  if (job.status === 'completed' && result) return <ChartView jobId={jobId} result={result} />

  const label = job.status === 'pending' ? STAGES.queued : STAGES[job.stage ?? ''] ?? 'Processing…'
  return (
    <div className="max-w-xl mx-auto bg-white rounded-lg border border-gray-200 p-6" data-testid="processing">
      <h2 className="text-lg font-medium text-gray-900 break-all">{job.filename}</h2>
      <p className="mt-1 text-sm text-gray-600" data-testid="stage">
        {label}
      </p>
      <div className="mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-600 transition-all duration-700"
          style={{ width: `${Math.max(2, job.progress)}%` }}
          data-testid="progress-bar"
        />
      </div>
      <p className="mt-2 text-xs text-gray-500 tabular-nums" data-testid="progress">
        {job.progress}%
      </p>
      <p className="mt-4 text-xs text-gray-500">
        You can leave this page open; the chart appears here when it is ready. The very first job also downloads the
        models (~250 MB).
      </p>
    </div>
  )
}
