import { useRef, useState, useCallback } from 'react'
import { ArrowUploadRegular, DismissCircleRegular } from '@fluentui/react-icons'
import { useUploadAttachment } from '../hooks/useAttachments'
import type { AttachmentResponse } from '../types/attachment'

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

interface PendingFile {
  file: File
  /** 0–100 upload progress */
  progress: number
  /** error message if upload failed */
  error: string | null
  /** id assigned after successful upload */
  uploadedId: string | null
}

interface AttachmentUploaderProps {
  taskId: string
  onUploaded?: (attachment: AttachmentResponse) => void
}

/**
 * Drag-and-drop (or click-to-select) file uploader for task attachments.
 * Supports multiple files, shows per-file progress bars, and enforces a
 * 10 MB size limit with inline error feedback.
 */
export default function AttachmentUploader({
  taskId,
  onUploaded,
}: AttachmentUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [pending, setPending] = useState<PendingFile[]>([])

  const uploadMutation = useUploadAttachment(taskId)

  // ---------------------------------------------------------------------------
  // Upload logic
  // ---------------------------------------------------------------------------

  const uploadFile = useCallback(
    (file: File) => {
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setPending((prev) => [
          ...prev,
          {
            file,
            progress: 0,
            error: `File exceeds 10 MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB)`,
            uploadedId: null,
          },
        ])
        return
      }

      // Add to pending list at 0%
      setPending((prev) => [
        ...prev,
        { file, progress: 0, error: null, uploadedId: null },
      ])

      // Simulate indeterminate progress while waiting for response
      const progressInterval = setInterval(() => {
        setPending((prev) =>
          prev.map((p) =>
            p.file === file && p.progress < 85 && !p.error && !p.uploadedId
              ? { ...p, progress: p.progress + 5 }
              : p,
          ),
        )
      }, 150)

      uploadMutation.mutate(file, {
        onSuccess: (attachment) => {
          clearInterval(progressInterval)
          setPending((prev) =>
            prev.map((p) =>
              p.file === file
                ? { ...p, progress: 100, uploadedId: attachment.id }
                : p,
            ),
          )
          onUploaded?.(attachment)
          // Auto-dismiss completed items after 1.5 s
          setTimeout(() => {
            setPending((prev) =>
              prev.filter((p) => p.file !== file),
            )
          }, 1500)
        },
        onError: (err: unknown) => {
          clearInterval(progressInterval)
          const message =
            err instanceof Error ? err.message : 'Upload failed'
          setPending((prev) =>
            prev.map((p) =>
              p.file === file ? { ...p, progress: 0, error: message } : p,
            ),
          )
        },
      })
    },
    [uploadMutation, onUploaded],
  )

  function handleFiles(files: FileList | null) {
    if (!files) return
    Array.from(files).forEach(uploadFile)
  }

  // ---------------------------------------------------------------------------
  // Drag handlers
  // ---------------------------------------------------------------------------

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function onDragLeave(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files)
    // Reset input so the same file can be re-uploaded after removal
    e.target.value = ''
  }

  function dismissError(file: File) {
    setPending((prev) => prev.filter((p) => p.file !== file))
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col gap-2">
      {/* Drop zone */}
      <button
        type="button"
        aria-label="Upload attachments — click or drag and drop files here"
        onClick={() => inputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`
          w-full border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
          transition-colors duration-150 select-none
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-bg-primary
          ${
            isDragOver
              ? 'border-accent bg-accent/5'
              : 'border-border hover:border-accent/50 hover:bg-bg-hover'
          }
        `}
      >
        <ArrowUploadRegular
          className={`
            w-6 h-6 mx-auto mb-2 transition-colors
            ${isDragOver ? 'text-accent' : 'text-text-tertiary'}
          `}
        />
        <p className="text-sm text-text-secondary">
          {isDragOver ? (
            <span className="text-accent font-medium">Drop files here</span>
          ) : (
            <>
              <span className="text-text-primary font-medium">
                Click to upload
              </span>{' '}
              or drag and drop
            </>
          )}
        </p>
        <p className="text-xs text-text-tertiary mt-1">
          Any file type, up to 10 MB each
        </p>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.zip,.md"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={onInputChange}
        />
      </button>

      {/* Per-file progress / error list */}
      {pending.length > 0 && (
        <div className="flex flex-col gap-1.5" aria-live="polite">
          {pending.map((item, idx) => (
            <div
              key={idx}
              className={`
                rounded-lg px-3 py-2 border
                ${item.error ? 'border-danger/40 bg-danger/5' : 'border-border bg-bg-tertiary'}
              `}
            >
              <div className="flex items-center gap-2">
                <span className="flex-1 text-xs text-text-primary truncate">
                  {item.file.name}
                </span>
                {item.error && (
                  <button
                    onClick={() => dismissError(item.file)}
                    className="flex-shrink-0 text-text-tertiary hover:text-text-primary transition-colors"
                    aria-label={`Dismiss error for ${item.file.name}`}
                  >
                    <DismissCircleRegular className="w-3.5 h-3.5" />
                  </button>
                )}
                {!item.error && (
                  <span className="flex-shrink-0 text-[10px] text-text-tertiary tabular-nums">
                    {item.progress < 100 ? `${item.progress}%` : 'Done'}
                  </span>
                )}
              </div>

              {/* Progress bar */}
              {!item.error && (
                <div className="mt-1.5 h-1 rounded-full bg-bg-hover overflow-hidden">
                  <div
                    className={`
                      h-full rounded-full transition-all duration-200
                      ${item.progress === 100 ? 'bg-success' : 'bg-accent'}
                    `}
                    style={{ width: `${item.progress}%` }}
                    role="progressbar"
                    aria-valuenow={item.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Upload progress for ${item.file.name}`}
                  />
                </div>
              )}

              {/* Error message */}
              {item.error && (
                <p className="mt-0.5 text-[10px] text-danger">{item.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
