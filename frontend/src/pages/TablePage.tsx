import { useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useParams, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowSortRegular,
  ArrowSortUpRegular,
  ArrowSortDownRegular,
  AddRegular,
  CircleRegular,
  CheckmarkCircleRegular,
  ArrowCircleRightRegular,
  ClockRegular,
  ErrorCircleRegular,
} from '@fluentui/react-icons'
import { FilterBar } from '../components/FilterBar'
import { useFilters } from '../hooks/useFilters'
import { listTasksApi, updateTaskStatusApi, updateTaskApi } from '../api/tasks'
import { teamsApi } from '../api/teams'
import { taskKeys } from '../hooks/useTasks'
import type { Task, TaskStatus, TaskPriority } from '../types/task'
import { TASK_STATUSES, PRIORITY_LABELS } from '../types/task'
import { STATUS_COLORS, PRIORITY_COLORS } from '../constants/task'
import { formatDate } from '../utils/date'
import { sortTasks } from './table/tableUtils'
import type { SortKey, SortDir } from './table/tableUtils'
import { useTableSort } from './table/useTableSort'

// ── Status helpers ────────────────────────────────────────────────────────────

/** Status display metadata with icon for inline status cells. */
const STATUS_META: Record<
  TaskStatus,
  { label: string; color: string; icon: React.ElementType }
> = {
  BACKLOG: { label: 'Backlog', color: STATUS_COLORS.BACKLOG, icon: CircleRegular },
  TODO: { label: 'Todo', color: STATUS_COLORS.TODO, icon: CircleRegular },
  PROGRESS: {
    label: 'In Progress',
    color: STATUS_COLORS.PROGRESS,
    icon: ArrowCircleRightRegular,
  },
  REVIEW: { label: 'Review', color: STATUS_COLORS.REVIEW, icon: ClockRegular },
  DONE: {
    label: 'Done',
    color: STATUS_COLORS.DONE,
    icon: CheckmarkCircleRegular,
  },
  REOPEN: {
    label: 'Reopen',
    color: STATUS_COLORS.REOPEN,
    icon: ErrorCircleRegular,
  },
  CLOSED: { label: 'Closed', color: STATUS_COLORS.CLOSED, icon: CheckmarkCircleRegular },
}

// ── Inline status dropdown ────────────────────────────────────────────────────

function StatusCell({
  taskId,
  status,
  projectId,
}: {
  taskId: string
  status: TaskStatus
  projectId: string
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const meta = STATUS_META[status]
  const Icon = meta.icon

  const mutation = useMutation({
    mutationFn: (next: TaskStatus) =>
      updateTaskStatusApi(taskId, { status: next }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: taskKeys.all(projectId),
      })
    },
  })

  return (
    <div className="relative">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono transition-colors duration-75 hover:bg-bg-hover"
        style={{ color: meta.color }}
        aria-label={`Status: ${meta.label}`}
      >
        <Icon style={{ fontSize: 13 }} />
        {meta.label}
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-20"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
            }}
          />
          <div className="absolute top-full mt-1 left-0 z-30 bg-bg-secondary border border-border rounded-lg shadow-xl shadow-black/40 overflow-hidden py-1 min-w-[140px]">
            {TASK_STATUSES.map((s) => {
              const m = STATUS_META[s]
              const SI = m.icon
              return (
                <button
                  key={s}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    mutation.mutate(s)
                    setOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-bg-hover transition-colors duration-75"
                  style={{ color: m.color }}
                >
                  <SI style={{ fontSize: 13 }} />
                  {m.label}
                  {s === status && (
                    <span className="ml-auto text-[10px] text-text-tertiary font-mono">✓</span>
                  )}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ── Inline priority dropdown ──────────────────────────────────────────────────

function PriorityCell({
  taskId,
  priority,
  projectId,
}: {
  taskId: string
  priority: TaskPriority
  projectId: string
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const color = PRIORITY_COLORS[priority]
  const label = PRIORITY_LABELS[priority]

  const mutation = useMutation({
    mutationFn: (p: TaskPriority) =>
      updateTaskApi(taskId, { priority: p }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: taskKeys.all(projectId),
      })
    },
  })

  return (
    <div className="relative">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono transition-colors duration-75 hover:bg-bg-hover"
        style={{ color }}
        aria-label={`Priority: ${label}`}
      >
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
        {label}
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-20"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
            }}
          />
          <div className="absolute top-full mt-1 left-0 z-30 bg-bg-secondary border border-border rounded-lg shadow-xl shadow-black/40 overflow-hidden py-1 min-w-[120px]">
            {([0, 1, 2, 3, 4] as TaskPriority[]).map((p) => {
              const c = PRIORITY_COLORS[p]
              const lbl = PRIORITY_LABELS[p]
              return (
                <button
                  key={p}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    mutation.mutate(p)
                    setOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-bg-hover transition-colors duration-75"
                  style={{ color: c }}
                >
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: c }} />
                  {lbl}
                  {p === priority && (
                    <span className="ml-auto text-[10px] text-text-tertiary font-mono">✓</span>
                  )}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ── Column header ─────────────────────────────────────────────────────────────

function ColHeader({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
}: {
  label: string
  sortKey: SortKey
  currentKey: SortKey
  currentDir: SortDir
  onSort: (k: SortKey) => void
}) {
  const active = currentKey === sortKey
  return (
    <th
      className="px-4 py-2.5 text-left cursor-pointer select-none group"
      onClick={() => onSort(sortKey)}
    >
      <div className="flex items-center gap-1.5 text-xs font-mono text-text-tertiary uppercase tracking-wider group-hover:text-text-secondary transition-colors duration-75">
        {label}
        <span className={active ? 'text-accent' : 'text-text-tertiary/40 group-hover:text-text-tertiary'}>
          {active ? (
            currentDir === 'asc' ? (
              <ArrowSortUpRegular style={{ fontSize: 11 }} />
            ) : (
              <ArrowSortDownRegular style={{ fontSize: 11 }} />
            )
          ) : (
            <ArrowSortRegular style={{ fontSize: 11 }} />
          )}
        </span>
      </div>
    </th>
  )
}

// ── TablePage ─────────────────────────────────────────────────────────────────

/**
 * Table view — sortable task list with inline status/priority editing.
 * Filters are synced to the URL via nuqs through useFilters.
 */
export default function TablePage() {
  const { t } = useTranslation()
  const { teamId = '', projKey = '' } = useParams<{
    teamId: string
    projKey: string
  }>()
  const navigate = useNavigate()

  const { sortKey, sortDir, handleSort } = useTableSort()

  const { filters } = useFilters()

  // Resolve project ID from team projects list
  const { data: projects } = useQuery({
    queryKey: ['projects', teamId],
    queryFn: () => teamsApi.listProjects(teamId),
    enabled: !!teamId,
  })

  const project = projects?.find((p) => p.key === projKey)

  const taskListParams = {
    status: filters.status.join(',') || undefined,
    assignee_id: filters.assignee === 'me' ? 'me' : undefined,
    priority: filters.priority.length === 1 ? filters.priority[0] : undefined,
    is_archived: false,
  }

  const { data: page, isLoading } = useQuery({
    queryKey: taskKeys.list(project?.id ?? '', taskListParams),
    queryFn: () => listTasksApi(project!.id, taskListParams),
    enabled: !!project?.id,
  })

  const tasks = useMemo(() => {
    let list = page?.items ?? []
    if (filters.unassigned) list = list.filter((t) => t.assignee_id === null)
    if (filters.priority.length > 1)
      list = list.filter((t) => filters.priority.includes(t.priority))
    return sortTasks(list, sortKey, sortDir)
  }, [page, filters, sortKey, sortDir])

  function openTask(number: number) {
    navigate(`/teams/${teamId}/projects/${projKey}/tasks/${number}`)
  }

  /** Scroll container ref for the virtualizer */
  const parentRef = useRef<HTMLDivElement>(null)

  const ROW_HEIGHT = 41 // px — matches py-2.5 rows

  const rowVirtualizer = useVirtualizer({
    count: tasks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  })

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-text-tertiary text-xs font-mono">
            {tasks.length} {t('table.tasks', 'tasks')}
          </span>
          <FilterBar />
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 h-7 px-3 rounded-md bg-accent text-white text-xs font-medium hover:bg-accent-hover transition-colors duration-100"
          aria-label={t('task.create')}
        >
          <AddRegular style={{ fontSize: 14 }} />
          {t('task.create')}
        </button>
      </div>

      {/* Table */}
      <div ref={parentRef} className="flex-1 overflow-auto min-h-0">
        {isLoading && !page ? (
          <div className="flex items-center justify-center h-32 text-text-tertiary text-xs font-mono">
            {t('common.loading')}
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <p className="text-text-tertiary text-sm font-mono">
              {t('table.empty', 'No tasks found')}
            </p>
          </div>
        ) : (
          <table className="w-full border-collapse" style={{ fontFamily: 'inherit' }}>
            <thead className="sticky top-0 bg-bg-primary z-10">
              <tr className="border-b border-border">
                <ColHeader
                  label="#"
                  sortKey="number"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <ColHeader
                  label={t('task.title')}
                  sortKey="title"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <ColHeader
                  label={t('task.status')}
                  sortKey="status"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <ColHeader
                  label={t('task.priority')}
                  sortKey="priority"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <th className="px-4 py-2.5 text-left">
                  <span className="text-xs font-mono text-text-tertiary uppercase tracking-wider">
                    {t('task.assignee')}
                  </span>
                </th>
                <ColHeader
                  label={t('table.dueDate', 'Due')}
                  sortKey="due_date"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <ColHeader
                  label={t('table.created', 'Created')}
                  sortKey="created_at"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
              </tr>
            </thead>
            {/* Virtual tbody: total height via spacer rows, only visible rows rendered */}
            <tbody>
              {rowVirtualizer.getTotalSize() > 0 && (
                <tr style={{ height: rowVirtualizer.getVirtualItems()[0]?.start ?? 0 }} aria-hidden />
              )}
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const task = tasks[virtualRow.index]
                return (
                  <TableRow
                    key={task.id}
                    task={task}
                    projectId={project?.id ?? ''}
                    projKey={projKey}
                    striped={virtualRow.index % 2 === 1}
                    onClick={() => openTask(task.number)}
                  />
                )
              })}
              {rowVirtualizer.getTotalSize() > 0 && (
                <tr
                  style={{
                    height:
                      rowVirtualizer.getTotalSize() -
                      (rowVirtualizer.getVirtualItems().at(-1)?.end ?? 0),
                  }}
                  aria-hidden
                />
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── TableRow ──────────────────────────────────────────────────────────────────

function TableRow({
  task,
  projectId,
  projKey,
  striped,
  onClick,
}: {
  task: Task
  projectId: string
  projKey: string
  striped: boolean
  onClick: () => void
}) {
  return (
    <tr
      onClick={onClick}
      className={[
        'border-b border-border/50 cursor-pointer transition-colors duration-75 group',
        striped ? 'bg-bg-secondary/40' : '',
        'hover:bg-bg-hover',
      ].join(' ')}
    >
      {/* Number */}
      <td className="px-4 py-2.5 w-16">
        <span className="text-xs font-mono text-text-tertiary">
          {projKey}-{task.number}
        </span>
      </td>

      {/* Title */}
      <td className="px-4 py-2.5 max-w-xs xl:max-w-lg">
        <span className="text-sm text-text-primary group-hover:text-white truncate block transition-colors duration-75">
          {task.title}
        </span>
      </td>

      {/* Status */}
      <td className="px-4 py-2.5 w-36" onClick={(e) => e.stopPropagation()}>
        <StatusCell
          taskId={task.id}
          status={task.status}
          projectId={projectId}
        />
      </td>

      {/* Priority */}
      <td className="px-4 py-2.5 w-28" onClick={(e) => e.stopPropagation()}>
        <PriorityCell
          taskId={task.id}
          priority={task.priority}
          projectId={projectId}
        />
      </td>

      {/* Assignee */}
      <td className="px-4 py-2.5 w-36">
        {task.assignee_id ? (
          <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary font-mono">
            <span className="w-5 h-5 rounded-full bg-bg-tertiary border border-border flex items-center justify-center text-[10px] text-text-tertiary">
              {task.assignee_id.slice(0, 2).toUpperCase()}
            </span>
          </span>
        ) : (
          <span className="text-xs text-text-tertiary font-mono">—</span>
        )}
      </td>

      {/* Due date */}
      <td className="px-4 py-2.5 w-28">
        <span
          className={[
            'text-xs font-mono',
            task.due_date && new Date(task.due_date) < new Date()
              ? 'text-danger'
              : 'text-text-tertiary',
          ].join(' ')}
        >
          {formatDate(task.due_date)}
        </span>
      </td>

      {/* Created */}
      <td className="px-4 py-2.5 w-28">
        <span className="text-xs font-mono text-text-tertiary">
          {formatDate(task.created_at)}
        </span>
      </td>
    </tr>
  )
}
