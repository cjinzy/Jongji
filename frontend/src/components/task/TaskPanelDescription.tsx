/**
 * TaskPanelDescription — description viewer/editor for TaskDetailPanel.
 */
import { useTranslation } from 'react-i18next'

interface TaskPanelDescriptionProps {
  description: string | null
  editing: boolean
  value: string
  onChange: (v: string) => void
  onSave: () => void
  onCancel: () => void
  onEditStart: () => void
}

export function TaskPanelDescription({
  description,
  editing,
  value,
  onChange,
  onSave,
  onCancel,
  onEditStart,
}: TaskPanelDescriptionProps) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
        {t('task.description')}
      </span>
      {editing ? (
        <div className="flex flex-col gap-2">
          <textarea
            autoFocus
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={5}
            className="
              bg-bg-tertiary border border-accent/50 rounded px-3 py-2
              text-sm text-text-primary resize-none
              focus:outline-none focus:border-accent
            "
          />
          <div className="flex gap-2">
            <button
              onClick={onSave}
              className="text-xs px-3 py-1 bg-accent text-white rounded hover:bg-accent-hover transition-colors"
            >
              {t('common.save')}
            </button>
            <button
              onClick={onCancel}
              className="text-xs px-3 py-1 bg-bg-hover text-text-secondary rounded hover:text-text-primary transition-colors"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : (
        <div
          onClick={onEditStart}
          className="
            min-h-[60px] bg-bg-tertiary border border-border rounded px-3 py-2
            text-sm text-text-secondary cursor-text
            hover:border-accent/40 transition-colors
          "
        >
          {description ? (
            <p className="whitespace-pre-wrap">{description}</p>
          ) : (
            <span className="text-text-tertiary italic">
              Click to add description...
            </span>
          )}
        </div>
      )}
    </div>
  )
}
