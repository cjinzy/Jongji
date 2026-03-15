/**
 * TaskDetailPanel — slide-in side panel for viewing and editing a task.
 *
 * Composed from sub-components:
 *   - TaskPanelHeader  (title editing + close)
 *   - TaskPanelMeta    (status, priority, assignee, dates, labels, tags)
 *   - TaskPanelDescription (description editor)
 *   - TaskPanelComments (comment list + input)
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useTask, useTaskComments, useUpdateTask, useCreateComment } from '../hooks/useTasks'
import type { TaskStatus, TaskPriority } from '../types/task'
import { TaskPanelHeader } from './task/TaskPanelHeader'
import { TaskPanelMeta } from './task/TaskPanelMeta'
import { TaskPanelDescription } from './task/TaskPanelDescription'
import { TaskPanelComments } from './task/TaskPanelComments'

interface TaskDetailPanelProps {
  taskId: string | null
  projectId: string
  onClose: () => void
  onStatusChange?: (taskId: string, status: TaskStatus) => void
}

export function TaskDetailPanel({
  taskId,
  projectId,
  onClose,
  onStatusChange,
}: TaskDetailPanelProps) {
  const { t } = useTranslation()
  const panelRef = useRef<HTMLDivElement>(null)

  const { data: task, isLoading } = useTask(taskId)
  const { data: comments } = useTaskComments(taskId)
  const updateTask = useUpdateTask(projectId)
  const createComment = useCreateComment(taskId ?? '')

  const [editingTitle, setEditingTitle] = useState(false)
  const [titleValue, setTitleValue] = useState('')
  const [editingDesc, setEditingDesc] = useState(false)
  const [descValue, setDescValue] = useState('')
  const [commentValue, setCommentValue] = useState('')
  const [localStatus, setLocalStatus] = useState<TaskStatus | null>(null)

  // Sync local state when task loads
  useEffect(() => {
    if (task) {
      setTitleValue(task.title)
      setDescValue(task.description ?? '')
      setLocalStatus(task.status)
    }
  }, [task])

  // Escape key closes panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Focus trap: focus panel on open
  useEffect(() => {
    if (taskId) {
      panelRef.current?.focus()
    }
  }, [taskId])

  const isOpen = !!taskId

  function saveTitle() {
    if (!task || titleValue.trim() === task.title) {
      setEditingTitle(false)
      return
    }
    updateTask.mutate({ taskId: task.id, payload: { title: titleValue.trim() } })
    setEditingTitle(false)
  }

  function cancelTitle() {
    if (task) setTitleValue(task.title)
    setEditingTitle(false)
  }

  function saveDesc() {
    if (!task) {
      setEditingDesc(false)
      return
    }
    updateTask.mutate({ taskId: task.id, payload: { description: descValue } })
    setEditingDesc(false)
  }

  function handleStatusChange(status: TaskStatus) {
    if (!task) return
    setLocalStatus(status)
    onStatusChange?.(task.id, status)
  }

  function handlePriorityChange(priority: TaskPriority) {
    if (!task) return
    updateTask.mutate({ taskId: task.id, payload: { priority } })
  }

  function submitComment() {
    if (!commentValue.trim() || !taskId) return
    createComment.mutate(
      { content: commentValue.trim() },
      { onSuccess: () => setCommentValue('') },
    )
  }

  const currentStatus: TaskStatus = localStatus ?? task?.status ?? 'BACKLOG'

  return (
    <>
      {/* Backdrop */}
      <div
        className={`
          fixed inset-0 bg-black/30 z-40 transition-opacity duration-200
          ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}
        `}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={task?.title ?? 'Task Detail'}
        className={`
          fixed right-0 top-0 h-full w-[480px] max-w-full
          bg-bg-secondary border-l border-border
          z-50 flex flex-col
          transform transition-transform duration-250 ease-out
          focus-visible:outline-none
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-sm text-text-tertiary animate-pulse">
              {t('common.loading')}
            </span>
          </div>
        )}

        {!isLoading && task && (
          <>
            <TaskPanelHeader
              projectKey={task.project_key}
              taskNumber={task.number}
              title={task.title}
              editingTitle={editingTitle}
              titleValue={titleValue}
              onTitleChange={setTitleValue}
              onEditStart={() => setEditingTitle(true)}
              onSaveTitle={saveTitle}
              onCancelTitle={cancelTitle}
              onClose={onClose}
            />

            {/* Body — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              <TaskPanelMeta
                currentStatus={currentStatus}
                priority={task.priority}
                assigneeId={task.assignee_id}
                startDate={task.start_date}
                dueDate={task.due_date}
                labels={task.labels}
                tags={task.tags}
                onStatusChange={handleStatusChange}
                onPriorityChange={handlePriorityChange}
              />

              <TaskPanelDescription
                description={task.description}
                editing={editingDesc}
                value={descValue}
                onChange={setDescValue}
                onSave={saveDesc}
                onCancel={() => {
                  setDescValue(task.description ?? '')
                  setEditingDesc(false)
                }}
                onEditStart={() => setEditingDesc(true)}
              />

              {/* Divider */}
              <div className="border-t border-border" />

              <TaskPanelComments
                comments={comments}
                value={commentValue}
                isPending={createComment.isPending}
                onChange={setCommentValue}
                onSubmit={submitComment}
              />
            </div>
          </>
        )}
      </div>
    </>
  )
}
