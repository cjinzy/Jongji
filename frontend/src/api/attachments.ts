import apiClient from './client'
import type { AttachmentResponse } from '../types/attachment'

/**
 * Attachment API — upload, attach to task, delete, and download URL helpers.
 */
export const attachmentsApi = {
  /**
   * Temporary upload for editor images (not yet linked to a task).
   */
  upload: async (file: File): Promise<AttachmentResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiClient.post<AttachmentResponse>(
      '/attachments/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return res.data
  },

  /**
   * Upload a file and attach it directly to a task.
   */
  attachToTask: async (
    taskId: string,
    file: File,
  ): Promise<AttachmentResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiClient.post<AttachmentResponse>(
      `/tasks/${taskId}/attachments`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return res.data
  },

  /**
   * List all attachments for a task.
   */
  listByTask: async (taskId: string): Promise<AttachmentResponse[]> => {
    const res = await apiClient.get<AttachmentResponse[]>(
      `/tasks/${taskId}/attachments`,
    )
    return res.data
  },

  /**
   * Delete an attachment by id.
   */
  remove: async (id: string): Promise<void> => {
    await apiClient.delete(`/attachments/${id}`)
  },

  /**
   * Resolve a public download URL for an attachment.
   */
  getDownloadUrl: (id: string): string => `/api/v1/attachments/${id}`,
}
