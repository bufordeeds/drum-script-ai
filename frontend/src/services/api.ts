import axios from 'axios'
import { 
  FileUploadResponse, 
  JobStatusResponse, 
  JobResultResponse 
} from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const transcriptionApi = {
  uploadFile: async (file: File): Promise<FileUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post<FileUploadResponse>(
      '/transcription/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const response = await api.get<JobStatusResponse>(
      `/transcription/jobs/${jobId}`
    )
    return response.data
  },

  getJobResult: async (jobId: string): Promise<JobResultResponse> => {
    const response = await api.get<JobResultResponse>(
      `/transcription/jobs/${jobId}/result`
    )
    return response.data
  },

  deleteJob: async (jobId: string): Promise<void> => {
    await api.delete(`/transcription/jobs/${jobId}`)
  },
}

export default api