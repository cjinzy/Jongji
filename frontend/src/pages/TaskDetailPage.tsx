import { useParams, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeftRegular,
  CalendarRegular,
  PersonRegular,
  CircleRegular,
  CheckmarkCircleRegular,
  ArrowCircleRightRegular,
  ClockRegular,
  ErrorCircleRegular,
} from '@fluentui/react-icons'
import { getTaskApi } from '../api/tasks'
import type { TaskStatus, TaskPriority } from '../types/task'
import { PRIORITY_LABELS } from '../types/task'

const STATUS_META: Record<
  TaskStatus,
  { label: string; color: string; icon: React.ElementType }
> = {
  BACKLOG: { label: 'Backlog', color: '#6B6B76', icon: CircleRegular },
  TODO: { label: 'Todo', color: '#A0A0A8', icon: CircleRegular },
  PROGRESS: { label: 'In Progress', color: '#5B6AF0', icon: ArrowCircleRightRegular },
  REVIEW: { label: 'Review', color: '#F59E0B', icon: ClockRegular },
  DONE: { label: 'Done', color: '#22C55E', icon: CheckmarkCircleRegular },
  REOPEN: { label: 'Reopen', color: '#EF4444', icon: ErrorCircleRegular },
  CLOSED: { label: 'Closed', color: '#444448', icon: CheckmarkCircleRegular },
}

const PRIORITY_COLOR: Record<TaskPriority, string> = {
  0: '#6B6B76',
  1: '#22C55E',
  2: '#F59E0B',
  3: '#EF4444',
  4: '#EF4444',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Full-page task detail view.
 * Displays all task metadata, description, and activity feed.
 */
export default function TaskDetailPage() {
  const { t } = useTranslation()
  const { teamId = '', projKey = '', number = '' } = useParams<{
    teamId: string
    projKey: string
    number: string
  }>()
  const navigate = useNavigate()
  const taskNumber = parseInt(number, 10)

  const { data: task, isLoading, error } = useQuery({
    queryKey: ['task', teamId, projKey, taskNumber],
    queryFn: () => getTaskApi(taskNumber.toString()),
    enabled: !!taskNumber,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-xs text-text-tertiary font-mono">{t('common.loading')}</p>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-text-secondary">
          {t('task.notFound', 'Task not found')}
        </p>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover transition-colors"
        >
          <ArrowLeftRegular style={{ fontSize: 13 }} />
          {t('common.back', 'Back')}
        </button>
      </div>
    )
  }

  const statusMeta = STATUS_META[task.status]
  const StatusIcon = statusMeta.icon
  const priorityColor = PRIORITY_COLOR[task.priority]

  return (
    <div className="min-h-full bg-bg-primary">
      {/* Top bar */}
      <div className="sticky top-0 z-10 flex items-center gap-3 px-6 py-3 border-b border-border bg-bg-primary/95 backdrop-blur-sm">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 h-7 px-2 rounded-md text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors duration-100"
        >
          <ArrowLeftRegular style={{ fontSize: 14 }} />
          {t('common.back', 'Back')}
        </button>
        <span className="text-text-tertiary text-xs font-mono">
          {projKey}-{task.number}
        </span>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Title */}
        <h1 className="text-2xl font-semibold text-text-primary tracking-tight mb-6 leading-snug">
          {task.title}
        </h1>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 mb-8 p-4 bg-bg-secondary border border-border rounded-xl">
          <MetaRow
            icon={StatusIcon}
            label={t('task.status')}
            value={statusMeta.label}
            color={statusMeta.color}
          />
          <MetaRow
            icon={PersonRegular}
            label={t('task.assignee')}
            value={task.assignee_id ?? t('filter.unassigned', 'Unassigned')}
            color={task.assignee_id ? undefined : '#6B6B76'}
          />
          <MetaRow
            icon={CircleRegular}
            label={t('task.priority')}
            value={PRIORITY_LABELS[task.priority]}
            color={priorityColor}
          />
          <MetaRow
            icon={CalendarRegular}
            label={t('table.dueDate', 'Due date')}
            value={formatDate(task.due_date)}
            color={
              task.due_date && new Date(task.due_date) < new Date()
                ? '#EF4444'
                : undefined
            }
          />
          <MetaRow
            icon={CalendarRegular}
            label={t('table.created', 'Created')}
            value={formatDate(task.created_at)}
          />
          {task.start_date && (
            <MetaRow
              icon={CalendarRegular}
              label={t('task.startDate', 'Start date')}
              value={formatDate(task.start_date)}
            />
          )}
        </div>

        {/* Description */}
        {task.description ? (
          <div className="mb-8">
            <h2 className="text-xs font-mono text-text-tertiary uppercase tracking-widest mb-3">
              {t('task.description')}
            </h2>
            <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
              {task.description}
            </div>
          </div>
        ) : (
          <div className="mb-8 px-4 py-3 border border-dashed border-border rounded-lg">
            <p className="text-xs text-text-tertiary font-mono">
              {t('task.noDescription', 'No description')}
            </p>
          </div>
        )}

        {/* Labels */}
        {task.labels.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xs font-mono text-text-tertiary uppercase tracking-widest mb-3">
              {t('task.labels', 'Labels')}
            </h2>
            <div className="flex flex-wrap gap-2">
              {task.labels.map((label) => (
                <span
                  key={label.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono border border-border bg-bg-secondary"
                  style={{ color: label.color }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: label.color }}
                  />
                  {label.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── MetaRow ───────────────────────────────────────────────────────────────────

function MetaRow({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color?: string
}) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon
        className="mt-0.5 flex-shrink-0 text-text-tertiary"
        style={{ fontSize: 14 }}
      />
      <div className="min-w-0">
        <p className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider mb-0.5">
          {label}
        </p>
        <p
          className="text-sm font-mono truncate"
          style={{ color: color ?? '#F0F0F3' }}
        >
          {value}
        </p>
      </div>
    </div>
  )
}
