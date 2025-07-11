import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ProcessingStatus from './components/ProcessingStatus'
import NotationPreview from './components/NotationPreview'
import ExportOptions from './components/ExportOptions'
import ErrorBoundary from './components/ErrorBoundary'
import DebugPanel from './components/DebugPanel'
import { TranscriptionJob } from './types'

function App() {
  const [currentJob, setCurrentJob] = useState<TranscriptionJob | null>(null)
  const [debugData, setDebugData] = useState<{ jobStatus: any, jobResult: any, isConnected: boolean } | null>(null)

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-gray-900">
                Drum Transcription Service
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Upload your audio and get accurate drum notation in seconds
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="space-y-8">
            {!currentJob ? (
              <FileUpload onUploadSuccess={setCurrentJob} />
            ) : (
              <>
                <ProcessingStatus 
                  job={currentJob} 
                  onJobUpdate={setCurrentJob} 
                  onDebugData={setDebugData}
                />
                
                {currentJob.status === 'completed' && currentJob.result && (
                  <>
                    <NotationPreview job={currentJob} />
                    <ExportOptions job={currentJob} />
                  </>
                )}
                
                {currentJob.status === 'error' && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h3 className="text-lg font-medium text-red-800">
                      Processing Failed
                    </h3>
                    <p className="mt-2 text-sm text-red-700">
                      {currentJob.errorMessage || 'An unexpected error occurred'}
                    </p>
                    <div className="mt-4 space-x-3">
                      <button
                        onClick={() => setCurrentJob(null)}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                      >
                        Try Again
                      </button>
                      <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
                      >
                        Refresh Page
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
        
        {/* Debug Panel - Only visible in development */}
        <DebugPanel
          job={currentJob}
          jobStatus={debugData?.jobStatus}
          jobResult={debugData?.jobResult}
          isConnected={debugData?.isConnected || false}
        />
      </div>
    </ErrorBoundary>
  )
}

export default App