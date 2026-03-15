/**
 * TaskPanelHeader — title editing + close button for TaskDetailPanel.
 */
import { DismissRegular, EditRegular, CheckmarkRegular } from '@fluentui/react-icons'

interface TaskPanelHeaderProps {
  projectKey: string | undefined
  taskNumber: number
  title: string
  editingTitle: boolean
  titleValue: string
  onTitleChange: (v: string) => void
  onEditStart: () => void
  onSaveTitle: () => void
  onCancelTitle: () => void
  onClose: () => void
}

export function TaskPanelHeader({
  projectKey,
  taskNumber,
  title,
  editingTitle,
  titleValue,
  onTitleChange,
  onEditStart,
  onSaveTitle,
  onCancelTitle,
  onClose,
}: TaskPanelHeaderProps) {
  return (
    <div className="flex items-start gap-3 px-5 pt-5 pb-3 border-b border-border flex-shrink-0">
      <div className="flex-1 min-w-0">
        {/* Project + number */}
        <div className="text-[11px] font-mono text-text-tertiary mb-1">
          {projectKey ?? 'JNG'}-{taskNumber}
        </div>

        {/* Title */}
        {editingTitle ? (
          <div className="flex items-center gap-2">
            <input
              autoFocus
              value={titleValue}
              onChange={(e) => onTitleChange(e.target.value)}
              onBlur={onSaveTitle}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onSaveTitle()
                if (e.key === 'Escape') onCancelTitle()
              }}
              className="
                flex-1 bg-bg-tertiary border border-accent/50 rounded px-2 py-1
                text-sm text-text-primary focus:outline-none focus:border-accent
              "
            />
            <button
              onClick={onSaveTitle}
              className="text-success hover:text-success/80 transition-colors"
            >
              <CheckmarkRegular className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-start gap-2 group/title">
            <h2 className="text-base font-semibold text-text-primary leading-snug flex-1">
              {title}
            </h2>
            <button
              onClick={onEditStart}
              className="
                opacity-0 group-hover/title:opacity-100
                text-text-tertiary hover:text-text-primary transition-all mt-0.5
              "
              aria-label="Edit title"
            >
              <EditRegular className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Close */}
      <button
        onClick={onClose}
        className="
          w-7 h-7 rounded flex items-center justify-center flex-shrink-0
          text-text-tertiary hover:text-text-primary hover:bg-bg-hover
          transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
        "
        aria-label="Close panel"
      >
        <DismissRegular className="w-4 h-4" />
      </button>
    </div>
  )
}
