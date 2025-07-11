import { useEffect } from 'react'
import { useJobStatus, useJobResult } from '@/hooks/useTranscription'
import { useWebSocket } from '@/hooks/useWebSocket'
import { TranscriptionJob, ProcessingStage, ProgressUpdate } from '@/types'

interface ProcessingStatusProps {
  job: TranscriptionJob
  onJobUpdate: (job: TranscriptionJob | null) => void
  onDebugData?: (data: { jobStatus: any, jobResult: any, isConnected: boolean }) => void
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

export default function ProcessingStatus({ job, onJobUpdate, onDebugData }: ProcessingStatusProps) {
  const { data: jobStatus, isLoading } = useJobStatus(job.id)
  const { data: jobResult } = useJobResult(job.id)
  
  
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

  // Send debug data to parent
  useEffect(() => {
    if (onDebugData) {
      onDebugData({
        jobStatus,
        jobResult,
        isConnected
      })
    }
  }, [jobStatus, jobResult, isConnected, onDebugData])

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
        
        {/* Completion notification with download links */}
        {isCompleted && jobResult && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-medium text-green-800">
                  Processing Complete!
                </h3>
                <p className="text-sm text-green-700 mt-1">
                  Your drum notation is ready. Download the files below:
                </p>
                
                {jobResult.download_urls && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {jobResult.download_urls.pdf && (
                      <a
                        href={jobResult.download_urls.pdf}
                        download
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      >
                        <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        Download PDF
                      </a>
                    )}
                    
                    {jobResult.download_urls.musicxml && (
                      <a
                        href={jobResult.download_urls.musicxml}
                        download
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      >
                        <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                        Download MusicXML
                      </a>
                    )}
                    
                    {jobResult.download_urls.midi && (
                      <a
                        href={jobResult.download_urls.midi}
                        download
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      >
                        <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                        Download MIDI
                      </a>
                    )}
                  </div>
                )}
                
                <div className="mt-4 pt-3 border-t border-green-200">
                  <button
                    onClick={() => onJobUpdate(null)}
                    className="text-sm text-green-700 hover:text-green-900 font-medium"
                  >
                    Process Another File
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}