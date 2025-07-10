export type JobStatus = 
  | 'pending'
  | 'uploading'
  | 'validating'
  | 'processing'
  | 'completed'
  | 'error'

export type ProcessingStage = 
  | 'uploading'
  | 'validating'
  | 'preprocessing'
  | 'source_separation'
  | 'transcribing'
  | 'post_processing'
  | 'generating_exports'
  | 'completed'

export interface TranscriptionJob {
  id: string
  filename: string
  status: JobStatus
  progress: number
  stage?: ProcessingStage
  errorMessage?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
  result?: TranscriptionResult
}

export interface TranscriptionResult {
  tempo: number
  timeSignature: string
  durationSeconds: number
  accuracyScore: number
}

export interface FileUploadResponse {
  jobId: string
  message: string
  status: JobStatus
}

export interface JobStatusResponse {
  id: string
  filename: string
  status: JobStatus
  progress: number
  stage?: ProcessingStage
  errorMessage?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
}

export interface JobResultResponse {
  jobId: string
  status: JobStatus
  result?: TranscriptionResult
  downloadUrls?: {
    musicxml: string
    midi: string
    pdf: string
  }
}

export interface ProgressUpdate {
  jobId: string
  status: JobStatus
  progress: number
  stage: ProcessingStage
  message?: string
}