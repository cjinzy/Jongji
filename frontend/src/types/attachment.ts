/**
 * Attachment domain types for Jongji file management.
 */

export interface Attachment {
  id: string
  task_id: string | null
  comment_id: string | null
  filename: string
  content_type: string
  size_bytes: number
  is_temp: boolean
  created_at: string
}

export interface AttachmentResponse extends Attachment {}
