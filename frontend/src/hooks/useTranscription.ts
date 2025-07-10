import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transcriptionApi } from '@/services/api'

export const useUploadFile = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: transcriptionApi.uploadFile,
    onSuccess: (data) => {
      queryClient.setQueryData(['job', data.jobId], {
        id: data.jobId,
        status: data.status,
        progress: 0,
      })
    },
  })
}

export const useJobStatus = (jobId: string | null, enabled = true) => {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => transcriptionApi.getJobStatus(jobId!),
    enabled: enabled && !!jobId,
    refetchInterval: (data) => {
      if (!data) return 1000
      const jobData = data as any
      if (jobData.status === 'completed' || jobData.status === 'error') {
        return false
      }
      return 1000 // Poll every second while processing
    },
  })
}

export const useJobResult = (jobId: string | null) => {
  return useQuery({
    queryKey: ['job-result', jobId],
    queryFn: () => transcriptionApi.getJobResult(jobId!),
    enabled: !!jobId,
  })
}

export const useDeleteJob = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: transcriptionApi.deleteJob,
    onSuccess: (_, jobId) => {
      queryClient.removeQueries({ queryKey: ['job', jobId] })
      queryClient.removeQueries({ queryKey: ['job-result', jobId] })
    },
  })
}