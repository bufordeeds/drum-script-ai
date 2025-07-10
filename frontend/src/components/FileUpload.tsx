import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useUploadFile } from '@/hooks/useTranscription'
import { TranscriptionJob } from '@/types'

interface FileUploadProps {
  onUploadSuccess: (job: TranscriptionJob) => void
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploadError, setUploadError] = useState<string | null>(null)
  const uploadMutation = useUploadFile()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return
    
    const file = acceptedFiles[0]
    setUploadError(null)
    
    uploadMutation.mutate(file, {
      onSuccess: (response) => {
        onUploadSuccess({
          id: response.jobId,
          filename: file.name,
          status: response.status,
          progress: 0,
          createdAt: new Date().toISOString(),
        })
      },
      onError: (error: any) => {
        setUploadError(error.response?.data?.detail || 'Upload failed')
      }
    })
  }, [uploadMutation, onUploadSuccess])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
    disabled: uploadMutation.isPending
  })

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <div className="text-center">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Upload Audio File
        </h2>
        
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 transition-colors cursor-pointer
            ${isDragActive 
              ? 'border-primary-500 bg-primary-50' 
              : 'border-gray-300 hover:border-gray-400'
            }
            ${uploadMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          <div className="text-center">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            
            <div className="mt-4">
              {uploadMutation.isPending ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                  <span className="text-sm text-gray-600">Uploading...</span>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-600">
                    {isDragActive
                      ? 'Drop the audio file here'
                      : 'Drag and drop an audio file here, or click to select'}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Supports MP3, WAV, M4A up to 10MB
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
        
        {uploadError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-700">{uploadError}</p>
          </div>
        )}
        
        <div className="mt-6 text-xs text-gray-500">
          <p>
            Your audio will be processed to extract drum notation. 
            Processing typically takes 30-60 seconds.
          </p>
        </div>
      </div>
    </div>
  )
}