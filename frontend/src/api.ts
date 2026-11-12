export type JobStatus = 'pending' | 'processing' | 'completed' | 'error'

export interface Job {
  id: string
  filename: string
  status: JobStatus
  stage?: string | null
  progress: number
  error_message?: string | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface JobSummary {
  duration_s: number
  tempo_bpm: number
  time_signature: [number, number]
  bars: number
  hits: number
  hits_per_drum: Record<string, number>
  models?: Record<string, string | null>
  timings_s?: Record<string, number>
}

export interface JobResult {
  job_id: string
  filename: string
  status: JobStatus
  summary?: JobSummary
  files?: Record<'hits' | 'musicxml' | 'midi' | 'mix' | 'drums', string>
}

export interface Hit {
  time_s: number
  drum: string
  velocity: number
  confidence: number
  bar?: number
  beat?: number
  div?: number
  slot?: number
}

export interface Bar {
  number: number
  start_s: number
  end_s: number
  beats: number[]
}

/** hits.json — the source of truth for a transcription. */
export interface HitsDoc {
  schema_version: number
  source: { filename: string; duration_s: number; sample_rate: number }
  beats: number[]
  downbeats: number[]
  hits: Hit[]
  time_signature: [number, number]
  tempo_bpm: number
  tempo_map: { time_s: number; bar: number; bpm: number }[]
  bars: Bar[]
}

const BASE = '/api/v1/transcription'

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not json */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const getJob = (id: string) => fetch(`${BASE}/jobs/${id}`).then((r) => json<Job>(r))
export const getResult = (id: string) => fetch(`${BASE}/jobs/${id}/result`).then((r) => json<JobResult>(r))
export const listJobs = () => fetch(`${BASE}/jobs?limit=10`).then((r) => json<Job[]>(r))

export const fileUrl = (id: string, name: string, download = false) =>
  `${BASE}/jobs/${id}/files/${name}${download ? '?download=1' : ''}`

/** Upload with progress (fetch cannot report upload progress, XHR can). */
export function uploadFile(file: File, onProgress: (fraction: number) => void): Promise<Job> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}/upload`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      let body: any = null
      try {
        body = JSON.parse(xhr.responseText)
      } catch {
        /* ignore */
      }
      if (xhr.status >= 200 && xhr.status < 300 && body) resolve(body as Job)
      else reject(new Error(body?.detail || `Upload failed (${xhr.status})`))
    }
    xhr.onerror = () => reject(new Error('Upload failed: could not reach the server'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}
