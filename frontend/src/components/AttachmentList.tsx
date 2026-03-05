import {
  AttachRegular,
  DocumentRegular,
  ImageRegular,
  DeleteRegular,
  DocumentPdfRegular,
  DocumentTextRegular,
  ArrowDownloadRegular,
} from '@fluentui/react-icons'
import { useTaskAttachments, useDeleteAttachment } from '../hooks/useAttachments'
import { attachmentsApi } from '../api/attachments'
import type { AttachmentResponse } from '../types/attachment'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format raw byte count into a human-readable string (e.g. "1.2 MB").
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function isImage(contentType: string): boolean {
  return contentType.startsWith('image/')
}

function isPdf(contentType: string): boolean {
  return contentType === 'application/pdf'
}

function isText(contentType: string): boolean {
  return contentType.startsWith('text/')
}

/** Pick the right Fluent icon component for a content type. */
function FileIcon({
  contentType,
  className,
}: {
  contentType: string
  className?: string
}) {
  if (isImage(contentType))
    return <ImageRegular className={className ?? 'w-4 h-4'} />
  if (isPdf(contentType))
    return <DocumentPdfRegular className={className ?? 'w-4 h-4'} />
  if (isText(contentType))
    return <DocumentTextRegular className={className ?? 'w-4 h-4'} />
  return <DocumentRegular className={className ?? 'w-4 h-4'} />
}

// ---------------------------------------------------------------------------
// Single attachment row
// ---------------------------------------------------------------------------

interface AttachmentItemProps {
  attachment: AttachmentResponse
  editable: boolean
  onDelete: (id: string) => void
  isDeleting: boolean
}

function AttachmentItem({
  attachment,
  editable,
  onDelete,
  isDeleting,
}: AttachmentItemProps) {
  const downloadUrl = attachmentsApi.getDownloadUrl(attachment.id)

  return (
    <div className="group flex items-center gap-3 p-2 rounded-lg hover:bg-bg-hover transition-colors">
      {/* Thumbnail or icon */}
      {isImage(attachment.content_type) ? (
        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 w-8 h-8 rounded overflow-hidden border border-border"
          aria-label={`Preview ${attachment.filename}`}
        >
          <img
            src={downloadUrl}
            alt={attachment.filename}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </a>
      ) : (
        <span className="flex-shrink-0 w-8 h-8 rounded bg-bg-tertiary border border-border flex items-center justify-center text-text-tertiary">
          <FileIcon contentType={attachment.content_type} className="w-4 h-4" />
        </span>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 group/link"
          download={attachment.filename}
          aria-label={`Download ${attachment.filename}`}
        >
          <span className="text-sm text-text-primary truncate group-hover/link:text-accent transition-colors">
            {attachment.filename}
          </span>
          <ArrowDownloadRegular className="w-3 h-3 text-text-tertiary opacity-0 group-hover/link:opacity-100 flex-shrink-0 transition-opacity" />
        </a>
        <span className="text-xs text-text-tertiary">
          {formatFileSize(attachment.size_bytes)}
        </span>
      </div>

      {/* Delete */}
      {editable && (
        <button
          onClick={() => onDelete(attachment.id)}
          disabled={isDeleting}
          className="
            flex-shrink-0 w-6 h-6 rounded flex items-center justify-center
            text-text-tertiary opacity-0 group-hover:opacity-100
            hover:text-danger hover:bg-danger/10
            disabled:opacity-30 disabled:cursor-not-allowed
            transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-danger
          "
          aria-label={`Delete ${attachment.filename}`}
        >
          <DeleteRegular className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface AttachmentListProps {
  taskId: string
  editable?: boolean
}

/**
 * Renders the list of attachments for a task.
 * Shows file icon (or image thumbnail), filename, size, and optional delete.
 */
export default function AttachmentList({
  taskId,
  editable = false,
}: AttachmentListProps) {
  const { data: attachments, isLoading } = useTaskAttachments(taskId)
  const deleteAttachment = useDeleteAttachment(taskId)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-2">
        <AttachRegular className="w-4 h-4 text-text-tertiary animate-pulse" />
        <span className="text-xs text-text-tertiary animate-pulse">
          Loading attachments...
        </span>
      </div>
    )
  }

  if (!attachments || attachments.length === 0) {
    return (
      <div className="flex items-center gap-2 py-2 text-text-tertiary">
        <AttachRegular className="w-4 h-4" />
        <span className="text-xs italic">No attachments</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-0.5" role="list" aria-label="Attachments">
      {attachments.map((attachment) => (
        <div key={attachment.id} role="listitem">
          <AttachmentItem
            attachment={attachment}
            editable={editable}
            onDelete={(id) => deleteAttachment.mutate(id)}
            isDeleting={
              deleteAttachment.isPending &&
              deleteAttachment.variables === attachment.id
            }
          />
        </div>
      ))}
    </div>
  )
}
