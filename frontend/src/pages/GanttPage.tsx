import { useState, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowSyncRegular } from '@fluentui/react-icons'
import { useProjectTasks } from '../hooks/useTasks'
import { useResolvedProjectId } from '../hooks/useResolvedProjectId'
import { TaskDetailPanel } from '../components/TaskDetailPanel'
import GanttChart, { type GanttTask, type ViewMode } from '../components/gantt/GanttChart'
import type { Task } from '../types/task'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Status → progress percentage mapping */
const STATUS_PROGRESS: Record<Task['status'], number> = {
  BACKLOG: 0,
  TODO: 5,
  PROGRESS: 50,
  REVIEW: 80,
  DONE: 100,
  REOPEN: 20,
  CLOSED: 100,
}

/** Add days to an ISO date string and return a new ISO date string */
function addDays(isoDate: string, days: number): string {
  const d = new Date(isoDate)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

/** Format a Date or ISO string to YYYY-MM-DD */
function toYMD(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value
  return d.toISOString().slice(0, 10)
}

/**
 * Convert a Task to a GanttTask.
 * Falls back to created_at as start and created_at + 7 days as end
 * when start_date / due_date are absent.
 */
function taskToGanttTask(task: Task): GanttTask {
  const createdYMD = toYMD(task.created_at)
  const start = task.start_date ? toYMD(task.start_date) : createdYMD
  const end = task.due_date
    ? toYMD(task.due_date)
    : addDays(start, 7)

  // Ensure end is always strictly after start (frappe-gantt requires this)
  const safeEnd = end <= start ? addDays(start, 1) : end

  return {
    id: task.id,
    name: task.title,
    start,
    end: safeEnd,
    progress: STATUS_PROGRESS[task.status] ?? 0,
    custom_class: `status-${task.status}`,
  }
}

// ---------------------------------------------------------------------------
// View mode toggle config
// ---------------------------------------------------------------------------

const VIEW_MODES: { label: string; value: ViewMode }[] = [
  { label: 'Day', value: 'Day' },
  { label: 'Week', value: 'Week' },
  { label: 'Month', value: 'Month' },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Gantt chart page — renders project tasks on a timeline.
 * Route: /teams/:teamId/projects/:projKey/gantt
 */
export default function GanttPage() {
  const { projectId } = useResolvedProjectId()
  const { t } = useTranslation()

  const { data, isLoading, error, refetch } = useProjectTasks(projectId)

  const [viewMode, setViewMode] = useState<ViewMode>('Week')
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  // Convert tasks to Gantt format — memoised to avoid unnecessary re-renders
  const ganttTasks = useMemo<GanttTask[]>(() => {
    if (!data?.items) return []
    return data.items
      .filter((t) => !t.is_archived)
      .map(taskToGanttTask)
  }, [data])

  const handleTaskClick = useCallback((ganttTask: GanttTask) => {
    setSelectedTaskId(ganttTask.id)
  }, [])

  const handleDateChange = useCallback(
    (_ganttTask: GanttTask, _start: Date, _end: Date) => {
      // Date changes via drag are noted here.
      // A full implementation would call useUpdateTask to persist them.
    },
    [],
  )

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col h-full bg-bg-primary overflow-hidden">
      {/* ── Toolbar ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border flex-shrink-0">
        <h1 className="text-sm font-semibold text-text-primary mr-2">
          {t('nav.gantt', 'Gantt')}
        </h1>

        {/* View mode toggle group */}
        <div
          role="group"
          aria-label="View mode"
          className="flex items-center rounded-md border border-border overflow-hidden"
        >
          {VIEW_MODES.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setViewMode(value)}
              aria-pressed={viewMode === value}
              className={[
                'px-3 py-1 text-xs font-medium transition-colors duration-100',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent',
                viewMode === value
                  ? 'bg-accent text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover bg-transparent',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Refresh */}
        <button
          onClick={() => refetch()}
          aria-label="Refresh tasks"
          className="
            flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border border-border
            text-text-secondary hover:text-text-primary hover:bg-bg-hover
            transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
          "
        >
          <ArrowSyncRegular className="w-3.5 h-3.5" />
        </button>

        <div className="flex-1" />

        {/* Task count badge */}
        {!isLoading && !error && (
          <span className="text-xs text-text-tertiary font-mono">
            {ganttTasks.length} {ganttTasks.length === 1 ? 'task' : 'tasks'}
          </span>
        )}
      </div>

      {/* ── Main chart area ─────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-text-tertiary animate-pulse">
              {t('common.loading', 'Loading…')}
            </span>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-danger">
              Failed to load tasks
            </span>
          </div>
        )}

        {!isLoading && !error && (
          <GanttChart
            tasks={ganttTasks}
            viewMode={viewMode}
            onTaskClick={handleTaskClick}
            onDateChange={handleDateChange}
          />
        )}
      </div>

      {/* ── Task detail side panel ──────────────────────────────────── */}
      <TaskDetailPanel
        taskId={selectedTaskId}
        projectId={projectId}
        onClose={() => setSelectedTaskId(null)}
        onStatusChange={() => {
          // Status changes from the panel invalidate via useUpdateTaskStatus internally
        }}
      />
    </div>
  )
}
