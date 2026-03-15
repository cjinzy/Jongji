/**
 * TaskPanelMeta — status, priority, assignee, dates, labels, tags metadata
 * section for TaskDetailPanel.
 */
import { useTranslation } from 'react-i18next'
import {
  CalendarLtrRegular,
  PersonRegular,
  TagRegular,
} from '@fluentui/react-icons'
import type { TaskStatus, TaskPriority, Label, Tag } from '../../types/task'
import { TASK_STATUSES } from '../../types/task'
import {
  STATUS_COLORS,
  STATUS_LABELS,
  PRIORITY_LABELS,
  PRIORITY_COLORS,
} from '../../constants/task'

interface TaskPanelMetaProps {
  currentStatus: TaskStatus
  priority: TaskPriority
  assigneeId: string | null | undefined
  startDate: string | null | undefined
  dueDate: string | null | undefined
  labels: Label[]
  tags: Tag[]
  onStatusChange: (status: TaskStatus) => void
  onPriorityChange: (priority: TaskPriority) => void
}

export function TaskPanelMeta({
  currentStatus,
  priority,
  assigneeId,
  startDate,
  dueDate,
  labels,
  tags,
  onStatusChange,
  onPriorityChange,
}: TaskPanelMetaProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-5">
      {/* Status + Priority row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Status selector */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
            {t('task.status')}
          </span>
          <select
            value={currentStatus}
            onChange={(e) => onStatusChange(e.target.value as TaskStatus)}
            className="
              bg-bg-tertiary border border-border rounded px-2 py-1
              text-xs font-medium focus:outline-none focus:border-accent
              cursor-pointer appearance-none pr-5
            "
            style={{ color: STATUS_COLORS[currentStatus] }}
          >
            {TASK_STATUSES.map((s) => (
              <option key={s} value={s} style={{ color: STATUS_COLORS[s] }}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>

        {/* Priority selector */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
            {t('task.priority')}
          </span>
          <select
            value={priority}
            onChange={(e) => onPriorityChange(Number(e.target.value) as TaskPriority)}
            className="
              bg-bg-tertiary border border-border rounded px-2 py-1
              text-xs font-medium focus:outline-none focus:border-accent
              cursor-pointer appearance-none pr-5
            "
            style={{ color: PRIORITY_COLORS[priority] }}
          >
            {([0, 1, 2, 3, 4] as TaskPriority[]).map((p) => (
              <option key={p} value={p} style={{ color: PRIORITY_COLORS[p] }}>
                {PRIORITY_LABELS[p]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Assignee */}
      <div className="flex flex-col gap-1">
        <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
          <PersonRegular className="w-3 h-3" />
          {t('task.assignee')}
        </span>
        <div className="text-sm text-text-secondary bg-bg-tertiary border border-border rounded px-3 py-1.5">
          {assigneeId ?? (
            <span className="text-text-tertiary italic">Unassigned</span>
          )}
        </div>
      </div>

      {/* Dates */}
      {(startDate || dueDate) && (
        <div className="flex items-center gap-4">
          {startDate && (
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                <CalendarLtrRegular className="w-3 h-3" />
                Start
              </span>
              <span className="text-xs text-text-secondary">
                {new Date(startDate).toLocaleDateString()}
              </span>
            </div>
          )}
          {dueDate && (
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                <CalendarLtrRegular className="w-3 h-3" />
                Due
              </span>
              <span className="text-xs text-text-secondary">
                {new Date(dueDate).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Labels */}
      {labels.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
            <TagRegular className="w-3 h-3" />
            Labels
          </span>
          <div className="flex flex-wrap gap-1.5">
            {labels.map((label) => (
              <span
                key={label.id}
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{
                  backgroundColor: label.color + '22',
                  color: label.color,
                  border: `1px solid ${label.color}44`,
                }}
              >
                {label.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
            Tags
          </span>
          <div className="flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span
                key={tag.id}
                className="text-xs px-2 py-0.5 rounded bg-bg-hover text-text-secondary border border-border"
              >
                #{tag.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
