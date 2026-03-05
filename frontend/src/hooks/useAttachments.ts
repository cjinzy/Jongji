import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { attachmentsApi } from '../api/attachments'
import type { AttachmentResponse } from '../types/attachment'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const attachmentKeys = {
  byTask: (taskId: string) => ['attachments', 'task', taskId] as const,
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all attachments for a task.
 */
export function useTaskAttachments(taskId: string | null) {
  return useQuery({
    queryKey: attachmentKeys.byTask(taskId ?? ''),
    queryFn: () => attachmentsApi.listByTask(taskId!),
    enabled: !!taskId,
    staleTime: 30 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Upload a file and attach it to a task.
 * Invalidates the task's attachment list on success.
 */
export function useUploadAttachment(taskId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => attachmentsApi.attachToTask(taskId, file),

    onSuccess: (newAttachment: AttachmentResponse) => {
      // Optimistically append to cached list
      queryClient.setQueryData(
        attachmentKeys.byTask(taskId),
        (old: AttachmentResponse[] | undefined) =>
          old ? [...old, newAttachment] : [newAttachment],
      )
    },

    onError: () => {
      // Refetch on error to keep list consistent
      queryClient.invalidateQueries({
        queryKey: attachmentKeys.byTask(taskId),
      })
    },
  })
}

/**
 * Delete an attachment by id.
 * Optimistically removes from cache, refetches on error.
 */
export function useDeleteAttachment(taskId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (attachmentId: string) => attachmentsApi.remove(attachmentId),

    onMutate: async (attachmentId: string) => {
      await queryClient.cancelQueries({
        queryKey: attachmentKeys.byTask(taskId),
      })
      const previous = queryClient.getQueryData<AttachmentResponse[]>(
        attachmentKeys.byTask(taskId),
      )
      queryClient.setQueryData(
        attachmentKeys.byTask(taskId),
        (old: AttachmentResponse[] | undefined) =>
          old ? old.filter((a) => a.id !== attachmentId) : [],
      )
      return { previous }
    },

    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          attachmentKeys.byTask(taskId),
          context.previous,
        )
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: attachmentKeys.byTask(taskId),
      })
    },
  })
}
