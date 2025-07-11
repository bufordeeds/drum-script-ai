import { useState, useEffect } from 'react'
import { TranscriptionJob } from '@/types'

interface DebugPanelProps {
  job: TranscriptionJob | null
  jobStatus: any
  jobResult: any
  isConnected: boolean
}

export default function DebugPanel({ job, jobStatus, jobResult, isConnected }: DebugPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [logs, setLogs] = useState<Array<{timestamp: string, message: string, data?: any}>>([])

  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  useEffect(() => {
    if (jobStatus) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: 'Job Status Updated',
        data: jobStatus
      }].slice(-10)) // Keep last 10 logs
    }
  }, [jobStatus])

  useEffect(() => {
    if (jobResult) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: 'Job Result Updated',
        data: jobResult
      }].slice(-10))
    }
  }, [jobResult])

  const clearLogs = () => setLogs([])
  
  const copyJobId = (jobId: string) => {
    navigator.clipboard.writeText(jobId)
    setLogs(prev => [...prev, {
      timestamp: new Date().toISOString(),
      message: 'Job ID copied to clipboard',
      data: { jobId }
    }].slice(-10))
  }

  const testApiCall = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/transcription/jobs/${jobId}`)
      const data = await response.json()
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: `Manual API Test (${response.status})`,
        data: { status: response.status, response: data }
      }].slice(-10))
    } catch (error) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: 'API Test Error',
        data: { error: error.message }
      }].slice(-10))
    }
  }

  const testResultCall = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/transcription/jobs/${jobId}/result`)
      const data = await response.json()
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: 'Manual Result Test',
        data: { status: response.status, response: data }
      }].slice(-10))
    } catch (error) {
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        message: 'Result Test Error',
        data: { error: error.message }
      }].slice(-10))
    }
  }

  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 text-white rounded-lg shadow-lg max-w-md">
      <div 
        className="flex items-center justify-between p-3 cursor-pointer bg-gray-800 rounded-t-lg"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-sm font-medium">🐛 Debug Panel</span>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-xs">{isExpanded ? '▼' : '▲'}</span>
        </div>
      </div>
      
      {isExpanded && (
        <div className="p-3 max-h-96 overflow-y-auto">
          {/* Current Job State */}
          <div className="mb-4">
            <h4 className="text-xs font-semibold text-gray-300 mb-2">Current Job</h4>
            <div className="bg-gray-800 rounded p-2 text-xs">
              {job ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span><span className="text-yellow-400">ID:</span> {job.id.substring(0, 8)}...</span>
                    <button
                      onClick={() => copyJobId(job.id)}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      Copy
                    </button>
                  </div>
                  <div><span className="text-yellow-400">Status:</span> {job.status}</div>
                  <div><span className="text-yellow-400">Progress:</span> {job.progress}%</div>
                  <div><span className="text-yellow-400">Created:</span> {job.createdAt}</div>
                  {job.startedAt && <div><span className="text-yellow-400">Started:</span> {job.startedAt}</div>}
                  {job.completedAt && <div><span className="text-yellow-400">Completed:</span> {job.completedAt}</div>}
                </div>
              ) : (
                <span className="text-gray-500">No job</span>
              )}
            </div>
          </div>

          {/* API Response States */}
          <div className="mb-4">
            <h4 className="text-xs font-semibold text-gray-300 mb-2">API States</h4>
            <div className="space-y-2">
              <div className="bg-gray-800 rounded p-2 text-xs">
                <div className="text-yellow-400">Job Status API:</div>
                <div className="text-gray-300">{jobStatus ? 'Loaded' : 'Not loaded'}</div>
              </div>
              <div className="bg-gray-800 rounded p-2 text-xs">
                <div className="text-yellow-400">Job Result API:</div>
                <div className="text-gray-300">{jobResult ? 'Loaded' : 'Not loaded'}</div>
              </div>
            </div>
          </div>

          {/* Manual Test Buttons */}
          {job && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-gray-300 mb-2">Manual Tests</h4>
              <div className="space-y-2">
                <button
                  onClick={() => testApiCall(job.id)}
                  className="w-full bg-blue-600 hover:bg-blue-700 rounded p-2 text-xs"
                >
                  Test Job Status API
                </button>
                <button
                  onClick={() => testResultCall(job.id)}
                  className="w-full bg-green-600 hover:bg-green-700 rounded p-2 text-xs"
                >
                  Test Job Result API
                </button>
              </div>
            </div>
          )}

          {/* Recent Logs */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-gray-300">Recent Logs</h4>
              <button
                onClick={clearLogs}
                className="text-xs text-gray-400 hover:text-white"
              >
                Clear
              </button>
            </div>
            <div className="bg-gray-800 rounded p-2 text-xs max-h-32 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="text-gray-500">No logs yet</div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="mb-2 border-b border-gray-700 pb-1">
                    <div className="text-yellow-400 text-xs">{log.timestamp.split('T')[1].split('.')[0]}</div>
                    <div className="text-white">{log.message}</div>
                    {log.data && (
                      <details className="mt-1">
                        <summary className="text-gray-400 cursor-pointer text-xs">Show Data</summary>
                        <pre className="text-xs text-gray-300 mt-1 overflow-x-auto">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Environment Info */}
          <div className="text-xs text-gray-500">
            <div>Environment: {process.env.NODE_ENV}</div>
            <div>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</div>
          </div>
        </div>
      )}
    </div>
  )
}