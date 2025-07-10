import { useState } from 'react'
import { useJobResult } from '@/hooks/useTranscription'
import { TranscriptionJob } from '@/types'

interface ExportOptionsProps {
  job: TranscriptionJob
}

export default function ExportOptions({ job }: ExportOptionsProps) {
  const [downloading, setDownloading] = useState<string | null>(null)
  const { data: jobResult } = useJobResult(job.id)

  const handleDownload = async (format: string) => {
    if (!jobResult?.downloadUrls || downloading) return

    setDownloading(format)
    try {
      const url = jobResult.downloadUrls[format as keyof typeof jobResult.downloadUrls]
      
      // Create download link
      const link = document.createElement('a')
      link.href = url
      link.download = `${job.filename.replace(/\.[^/.]+$/, '')}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (error) {
      console.error('Download failed:', error)
    } finally {
      setDownloading(null)
    }
  }

  const exportOptions = [
    {
      format: 'pdf',
      name: 'PDF',
      description: 'Printable sheet music',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      color: 'bg-red-500 hover:bg-red-600'
    },
    {
      format: 'midi',
      name: 'MIDI',
      description: 'For DAW import',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zm12-3c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2z" />
        </svg>
      ),
      color: 'bg-blue-500 hover:bg-blue-600'
    },
    {
      format: 'musicxml',
      name: 'MusicXML',
      description: 'For MuseScore, Sibelius',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      ),
      color: 'bg-green-500 hover:bg-green-600'
    }
  ]

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Export Options
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {exportOptions.map((option) => (
          <div key={option.format} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3 mb-3">
              <div className={`p-2 rounded-lg text-white ${option.color}`}>
                {option.icon}
              </div>
              <div>
                <h4 className="font-medium text-gray-900">{option.name}</h4>
                <p className="text-sm text-gray-600">{option.description}</p>
              </div>
            </div>
            
            <button
              onClick={() => handleDownload(option.format)}
              disabled={!jobResult?.downloadUrls || downloading === option.format}
              className={`
                w-full flex items-center justify-center space-x-2 py-2 px-4 rounded-md text-sm font-medium
                ${jobResult?.downloadUrls
                  ? `${option.color} text-white focus:outline-none focus:ring-2 focus:ring-offset-2`
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }
              `}
            >
              {downloading === option.format ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Downloading...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>Download</span>
                </>
              )}
            </button>
          </div>
        ))}
      </div>
      
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h4 className="font-medium text-blue-900 mb-2">Export Information</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• PDF: Ready-to-print drum notation</li>
          <li>• MIDI: Compatible with all major DAWs</li>
          <li>• MusicXML: Import into notation software</li>
        </ul>
      </div>
    </div>
  )
}