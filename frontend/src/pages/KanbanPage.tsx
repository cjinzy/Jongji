import { useState, useMemo, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { useTranslation } from 'react-i18next'
import { PersonRegular, AddRegular, ArrowSyncRegular } from '@fluentui/react-icons'
import { KanbanColumn } from '../components/kanban/KanbanColumn'
import { KanbanCard } from '../components/kanban/KanbanCard'
import { TaskDetailPanel } from '../components/TaskDetailPanel'
import { TaskCreateModal } from '../components/TaskCreateModal'
import { useProjectTasks, useUpdateTaskStatus } from '../hooks/useTasks'
import { useResolvedProjectId } from '../hooks/useResolvedProjectId'
import type { Task, TaskStatus } from '../types/task'
import { TASK_STATUSES } from '../types/task'

// ---------------------------------------------------------------------------
// Column configuration
// ---------------------------------------------------------------------------
const COLUMN_CONFIG: Record<
  TaskStatus,
  { label: string; color: string }
> = {
  BACKLOG: { label: 'Backlog', color: '#6B6B76' },
  TODO: { label: 'Todo', color: '#5B6AF0' },
  PROGRESS: { label: 'In Progress', color: '#F59E0B' },
  REVIEW: { label: 'In Review', color: '#8B5CF6' },
  DONE: { label: 'Done', color: '#22C55E' },
  REOPEN: { label: 'Reopened', color: '#EF4444' },
  CLOSED: { label: 'Closed', color: '#374151' },
}

/**
 * Kanban board view with drag-and-drop between status columns.
 * Implements optimistic UI: tasks move immediately on drop, rolling back on error.
 */
export default function KanbanPage() {
  const { projectId } = useResolvedProjectId()
  const { t } = useTranslation()

  // ---------------------------------------------------------------------------
  // Data
  // ---------------------------------------------------------------------------
  const { data, isLoading, error, refetch } = useProjectTasks(projectId)
  const updateStatus = useUpdateTaskStatus(projectId)

  // ---------------------------------------------------------------------------
  // UI state
  // ---------------------------------------------------------------------------
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createModalStatus, setCreateModalStatus] = useState<TaskStatus | null>(null)
  const [unassignedOnly, setUnassignedOnly] = useState(false)

  // ---------------------------------------------------------------------------
  // Derived: tasks grouped by status
  // ---------------------------------------------------------------------------
  const tasksByStatus = useMemo<Record<TaskStatus, Task[]>>(() => {
    const base: Record<TaskStatus, Task[]> = {
      BACKLOG: [],
      TODO: [],
      PROGRESS: [],
      REVIEW: [],
      DONE: [],
      REOPEN: [],
      CLOSED: [],
    }
    if (!data?.items) return base

    const tasks = unassignedOnly
      ? data.items.filter((t) => !t.assignee_id)
      : data.items

    for (const task of tasks) {
      if (base[task.status]) {
        base[task.status].push(task)
      }
    }
    return base
  }, [data, unassignedOnly])

  // ---------------------------------------------------------------------------
  // DnD sensors
  // ---------------------------------------------------------------------------
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  function handleDragStart(event: DragStartEvent) {
    const draggedId = event.active.id as string
    const task = data?.items.find((t) => t.id === draggedId) ?? null
    setActiveTask(task)
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTask(null)
    const { active, over } = event
    if (!over) return

    const taskId = active.id as string
    const overId = over.id as string

    // Determine target status: over.id is either a TaskStatus (column) or a task id
    const targetStatus: TaskStatus | null = TASK_STATUSES.includes(overId as TaskStatus)
      ? (overId as TaskStatus)
      : (data?.items.find((t) => t.id === overId)?.status ?? null)

    if (!targetStatus) return

    const task = data?.items.find((t) => t.id === taskId)
    if (!task || task.status === targetStatus) return

    // Fire optimistic mutation (rolls back on error)
    updateStatus.mutate({ taskId, status: targetStatus })
  }

  // ---------------------------------------------------------------------------
  // Panel / modal callbacks
  // ---------------------------------------------------------------------------
  const handleCardClick = useCallback((task: Task) => {
    setSelectedTaskId(task.id)
  }, [])

  const handleAddTask = useCallback((status: TaskStatus) => {
    setCreateModalStatus(status)
  }, [])

  const handleStatusChangeFromPanel = useCallback(
    (taskId: string, status: TaskStatus) => {
      updateStatus.mutate({ taskId, status })
    },
    [updateStatus],
  )

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col h-full bg-bg-primary overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border flex-shrink-0">
        <h1 className="text-sm font-semibold text-text-primary mr-2">
          {t('nav.kanban')}
        </h1>

        {/* Unassigned filter */}
        <button
          onClick={() => setUnassignedOnly((v) => !v)}
          className={`
            flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border transition-colors
            focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
            ${
              unassignedOnly
                ? 'bg-accent/15 border-accent/40 text-accent'
                : 'bg-transparent border-border text-text-secondary hover:text-text-primary hover:bg-bg-hover'
            }
          `}
          aria-pressed={unassignedOnly}
        >
          <PersonRegular className="w-3.5 h-3.5" />
          Unassigned
        </button>

        {/* Refresh */}
        <button
          onClick={() => refetch()}
          className="
            flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border border-border
            text-text-secondary hover:text-text-primary hover:bg-bg-hover
            transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
          "
          aria-label="Refresh tasks"
        >
          <ArrowSyncRegular className="w-3.5 h-3.5" />
        </button>

        <div className="flex-1" />

        {/* Quick create */}
        <button
          onClick={() => setCreateModalStatus('TODO')}
          className="
            flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md
            bg-accent text-white font-medium
            hover:bg-accent-hover transition-colors
            focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
          "
        >
          <AddRegular className="w-3.5 h-3.5" />
          {t('task.create')}
        </button>
      </div>

      {/* Board area */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-text-tertiary animate-pulse">
              {t('common.loading')}
            </span>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm text-danger">Failed to load tasks</span>
          </div>
        )}

        {!isLoading && !error && (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="flex gap-3 px-5 py-4 h-full min-h-0">
              {TASK_STATUSES.map((status) => (
                <KanbanColumn
                  key={status}
                  status={status}
                  label={COLUMN_CONFIG[status].label}
                  tasks={tasksByStatus[status]}
                  accentColor={COLUMN_CONFIG[status].color}
                  onCardClick={handleCardClick}
                  onAddTask={handleAddTask}
                />
              ))}
            </div>

            {/* Drag overlay — ghost card while dragging */}
            <DragOverlay dropAnimation={null}>
              {activeTask ? (
                <div className="rotate-1 scale-105 opacity-90 pointer-events-none">
                  <KanbanCard
                    task={activeTask}
                    isBlocked={false}
                    onClick={() => {}}
                  />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
      </div>

      {/* Task detail side panel */}
      <TaskDetailPanel
        taskId={selectedTaskId}
        projectId={projectId}
        onClose={() => setSelectedTaskId(null)}
        onStatusChange={handleStatusChangeFromPanel}
      />

      {/* Task create modal */}
      <TaskCreateModal
        projectId={projectId}
        defaultStatus={createModalStatus ?? 'TODO'}
        isOpen={createModalStatus !== null}
        onClose={() => setCreateModalStatus(null)}
      />
    </div>
  )
}
