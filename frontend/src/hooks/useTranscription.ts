import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transcriptionApi } from '@/services/api'

export const useUploadFile = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: transcriptionApi.uploadFile,
    onSuccess: (data) => {
      queryClient.setQueryData(['job', data.job_id], {
        id: data.job_id,
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
      // Stop polling when job reaches terminal state
      if (jobData.status === 'completed' || jobData.status === 'error') {
        return false
      }
      return 1000 // Poll every second while processing
    },
    refetchIntervalInBackground: false, // Stop polling when tab is not active
  })
}

export const useJobResult = (jobId: string | null, jobCompleted: boolean = false) => {
  return useQuery({
    queryKey: ['job-result', jobId],
    queryFn: () => transcriptionApi.getJobResult(jobId!),
    enabled: !!jobId && jobCompleted,
    retry: 3,
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    refetchOnMount: false, // Don't refetch when component mounts
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
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