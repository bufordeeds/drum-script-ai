import { useEffect, useRef } from 'react'
import { TranscriptionJob } from '@/types'

interface NotationPreviewProps {
  job: TranscriptionJob
}

export default function NotationPreview({ job }: NotationPreviewProps) {
  const notationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (notationRef.current && job.result) {
      renderNotation()
    }
  }, [job.result])

  const renderNotation = async () => {
    if (!notationRef.current) return

    try {
      // TODO: Implement VexFlow notation rendering
      // For now, show a placeholder
      notationRef.current.innerHTML = `
        <div class="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <svg class="w-12 h-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zm12-3c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2z"/>
          </svg>
          <p class="text-sm text-gray-600 text-center">
            Notation preview will be displayed here<br/>
            <span class="text-xs text-gray-500">VexFlow integration coming soon</span>
          </p>
        </div>
      `
    } catch (error) {
      console.error('Failed to render notation:', error)
      notationRef.current.innerHTML = `
        <div class="text-center text-red-600 p-4">
          <p>Failed to render notation preview</p>
        </div>
      `
    }
  }

  if (!job.result) {
    return null
  }

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Notation Preview
      </h3>
      
      <div className="space-y-4">
        {/* Transcription Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="font-medium text-gray-900">Tempo</div>
            <div className="text-gray-600">{job.result.tempo} BPM</div>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="font-medium text-gray-900">Time Signature</div>
            <div className="text-gray-600">{job.result.timeSignature}</div>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="font-medium text-gray-900">Duration</div>
            <div className="text-gray-600">{Math.round(job.result.durationSeconds)}s</div>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="font-medium text-gray-900">Accuracy</div>
            <div className="text-gray-600">{Math.round(job.result.accuracyScore * 100)}%</div>
          </div>
        </div>
        
        {/* Notation Display */}
        <div className="border rounded-lg">
          <div ref={notationRef} className="min-h-[200px]" />
        </div>
        
        {/* Playback Controls (placeholder) */}
        <div className="flex items-center justify-center space-x-4 p-4 bg-gray-50 rounded-lg">
          <button className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            <span>Play</span>
          </button>
          
          <div className="text-sm text-gray-600">
            Audio playback coming soon
          </div>
        </div>
      </div>
    </div>
  )
}