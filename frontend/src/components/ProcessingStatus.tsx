import { useEffect } from 'react'
import { useJobStatus } from '@/hooks/useTranscription'
import { useWebSocket } from '@/hooks/useWebSocket'
import { TranscriptionJob, ProcessingStage, ProgressUpdate } from '@/types'

interface ProcessingStatusProps {
  job: TranscriptionJob
  onJobUpdate: (job: TranscriptionJob) => void
}

const stageLabels: Record<ProcessingStage, string> = {
  uploading: 'Uploading file...',
  validating: 'Validating audio...',
  preprocessing: 'Preprocessing audio...',
  source_separation: 'Separating drum track...',
  transcribing: 'Transcribing drums...',
  post_processing: 'Processing results...',
  generating_exports: 'Generating exports...',
  completed: 'Completed!'
}

export default function ProcessingStatus({ job, onJobUpdate }: ProcessingStatusProps) {
  const { data: jobStatus, isLoading } = useJobStatus(job.id)
  
  // WebSocket for real-time updates
  const { isConnected } = useWebSocket(job.id, (update: ProgressUpdate) => {
    // Update job with real-time progress
    onJobUpdate({
      ...job,
      status: update.status,
      progress: update.progress,
      stage: update.stage,
    })
  })

  useEffect(() => {
    if (jobStatus) {
      onJobUpdate({
        id: jobStatus.id,
        filename: jobStatus.filename,
        status: jobStatus.status,
        progress: jobStatus.progress,
        stage: jobStatus.stage,
        errorMessage: jobStatus.errorMessage,
        createdAt: jobStatus.createdAt,
        startedAt: jobStatus.startedAt,
        completedAt: jobStatus.completedAt,
      })
    }
  }, [jobStatus, onJobUpdate])

  if (isLoading && !jobStatus) {
    return (
      <div className="bg-white shadow-sm rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-2 bg-gray-200 rounded w-full mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  const currentJob = jobStatus || job
  const isCompleted = currentJob.status === 'completed'
  const isError = currentJob.status === 'error'
  const isProcessing = ['pending', 'processing', 'validating'].includes(currentJob.status)

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          Processing: {currentJob.filename}
        </h3>
        
        <div className="flex items-center space-x-2">
          {isProcessing && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
          )}
          
          {/* WebSocket connection indicator */}
          <div className={`
            w-2 h-2 rounded-full
            ${isConnected ? 'bg-green-500' : 'bg-gray-300'}
          `} title={isConnected ? 'Live updates active' : 'Live updates disconnected'} />
          
          <span className={`
            px-2 py-1 rounded-full text-xs font-medium
            ${isCompleted 
              ? 'bg-green-100 text-green-800' 
              : isError 
              ? 'bg-red-100 text-red-800'
              : 'bg-blue-100 text-blue-800'
            }
          `}>
            {isCompleted ? 'Completed' : isError ? 'Error' : 'Processing'}
          </span>
        </div>
      </div>
      
      <div className="space-y-4">
        {/* Progress Bar */}
        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{currentJob.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`
                h-2 rounded-full transition-all duration-300
                ${isCompleted 
                  ? 'bg-green-500' 
                  : isError 
                  ? 'bg-red-500'
                  : 'bg-primary-600'
                }
              `}
              style={{ width: `${currentJob.progress}%` }}
            />
          </div>
        </div>
        
        {/* Current Stage */}
        {currentJob.stage && (
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Current stage:</span>
            <span className="text-sm font-medium text-gray-900">
              {stageLabels[currentJob.stage] || currentJob.stage}
            </span>
          </div>
        )}
        
        {/* Timestamps */}
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <span className="font-medium">Started:</span>
            <div>{new Date(currentJob.startedAt || currentJob.createdAt).toLocaleString()}</div>
          </div>
          
          {currentJob.completedAt && (
            <div>
              <span className="font-medium">Completed:</span>
              <div>{new Date(currentJob.completedAt).toLocaleString()}</div>
            </div>
          )}
        </div>
        
        {/* Processing Info */}
        {isProcessing && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-sm text-blue-700">
              Your audio is being processed. This typically takes 30-60 seconds.
              You can close this page and return later - we'll save your progress.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}