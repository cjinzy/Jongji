import {
  DocumentRegular,
  ImageRegular,
  DocumentPdfRegular,
  DocumentTextRegular,
} from '@fluentui/react-icons'

// ---------------------------------------------------------------------------
// Format helpers
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

// ---------------------------------------------------------------------------
// Content-type predicates
// ---------------------------------------------------------------------------

export function isImage(contentType: string): boolean {
  return contentType.startsWith('image/')
}

export function isPdf(contentType: string): boolean {
  return contentType === 'application/pdf'
}

export function isText(contentType: string): boolean {
  return contentType.startsWith('text/')
}

// ---------------------------------------------------------------------------
// Icon component
// ---------------------------------------------------------------------------

/** Pick the right Fluent icon component for a content type. */
export function FileIcon({
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
