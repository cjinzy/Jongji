import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  DismissRegular,
  EditRegular,
  CheckmarkRegular,
  CommentRegular,
  SendRegular,
  CalendarLtrRegular,
  PersonRegular,
  TagRegular,
} from '@fluentui/react-icons'
import { useTask, useTaskComments, useUpdateTask, useCreateComment } from '../hooks/useTasks'
import type { TaskStatus, TaskPriority } from '../types/task'
import { TASK_STATUSES, PRIORITY_LABELS } from '../types/task'

interface TaskDetailPanelProps {
  taskId: string | null
  projectId: string
  onClose: () => void
  onStatusChange?: (taskId: string, status: TaskStatus) => void
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  BACKLOG: '#6B6B76',
  TODO: '#5B6AF0',
  PROGRESS: '#F59E0B',
  REVIEW: '#8B5CF6',
  DONE: '#22C55E',
  REOPEN: '#EF4444',
  CLOSED: '#374151',
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  BACKLOG: 'Backlog',
  TODO: 'Todo',
  PROGRESS: 'In Progress',
  REVIEW: 'In Review',
  DONE: 'Done',
  REOPEN: 'Reopened',
  CLOSED: 'Closed',
}

const PRIORITY_COLORS: Record<TaskPriority, string> = {
  0: '#6B6B76',
  1: '#22C55E',
  2: '#F59E0B',
  3: '#EF4444',
  4: '#EF4444',
}

/** Relative time formatter */
function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
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
            {/* Header */}
            <div className="flex items-start gap-3 px-5 pt-5 pb-3 border-b border-border flex-shrink-0">
              <div className="flex-1 min-w-0">
                {/* Project + number */}
                <div className="text-[11px] font-mono text-text-tertiary mb-1">
                  {task.project_key ?? 'JNG'}-{task.number}
                </div>

                {/* Title */}
                {editingTitle ? (
                  <div className="flex items-center gap-2">
                    <input
                      autoFocus
                      value={titleValue}
                      onChange={(e) => setTitleValue(e.target.value)}
                      onBlur={saveTitle}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveTitle()
                        if (e.key === 'Escape') {
                          setTitleValue(task.title)
                          setEditingTitle(false)
                        }
                      }}
                      className="
                        flex-1 bg-bg-tertiary border border-accent/50 rounded px-2 py-1
                        text-sm text-text-primary focus:outline-none focus:border-accent
                      "
                    />
                    <button
                      onClick={saveTitle}
                      className="text-success hover:text-success/80 transition-colors"
                    >
                      <CheckmarkRegular className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-start gap-2 group/title">
                    <h2 className="text-base font-semibold text-text-primary leading-snug flex-1">
                      {task.title}
                    </h2>
                    <button
                      onClick={() => setEditingTitle(true)}
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

            {/* Body — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

              {/* Status + Priority row */}
              <div className="flex items-center gap-3 flex-wrap">
                {/* Status selector */}
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
                    {t('task.status')}
                  </span>
                  <select
                    value={currentStatus}
                    onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
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
                    value={task.priority}
                    onChange={(e) => handlePriorityChange(Number(e.target.value) as TaskPriority)}
                    className="
                      bg-bg-tertiary border border-border rounded px-2 py-1
                      text-xs font-medium focus:outline-none focus:border-accent
                      cursor-pointer appearance-none pr-5
                    "
                    style={{ color: PRIORITY_COLORS[task.priority] }}
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
                  {task.assignee_id ?? (
                    <span className="text-text-tertiary italic">Unassigned</span>
                  )}
                </div>
              </div>

              {/* Dates */}
              {(task.start_date || task.due_date) && (
                <div className="flex items-center gap-4">
                  {task.start_date && (
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                        <CalendarLtrRegular className="w-3 h-3" />
                        Start
                      </span>
                      <span className="text-xs text-text-secondary">
                        {new Date(task.start_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  {task.due_date && (
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                        <CalendarLtrRegular className="w-3 h-3" />
                        Due
                      </span>
                      <span className="text-xs text-text-secondary">
                        {new Date(task.due_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Labels */}
              {task.labels.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                    <TagRegular className="w-3 h-3" />
                    Labels
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {task.labels.map((label) => (
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
              {task.tags.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
                    Tags
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {task.tags.map((tag) => (
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

              {/* Description */}
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-text-tertiary uppercase tracking-wide">
                  {t('task.description')}
                </span>
                {editingDesc ? (
                  <div className="flex flex-col gap-2">
                    <textarea
                      autoFocus
                      value={descValue}
                      onChange={(e) => setDescValue(e.target.value)}
                      rows={5}
                      className="
                        bg-bg-tertiary border border-accent/50 rounded px-3 py-2
                        text-sm text-text-primary resize-none
                        focus:outline-none focus:border-accent
                      "
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={saveDesc}
                        className="text-xs px-3 py-1 bg-accent text-white rounded hover:bg-accent-hover transition-colors"
                      >
                        {t('common.save')}
                      </button>
                      <button
                        onClick={() => {
                          setDescValue(task.description ?? '')
                          setEditingDesc(false)
                        }}
                        className="text-xs px-3 py-1 bg-bg-hover text-text-secondary rounded hover:text-text-primary transition-colors"
                      >
                        {t('common.cancel')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    onClick={() => setEditingDesc(true)}
                    className="
                      min-h-[60px] bg-bg-tertiary border border-border rounded px-3 py-2
                      text-sm text-text-secondary cursor-text
                      hover:border-accent/40 transition-colors
                    "
                  >
                    {task.description ? (
                      <p className="whitespace-pre-wrap">{task.description}</p>
                    ) : (
                      <span className="text-text-tertiary italic">
                        Click to add description...
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Divider */}
              <div className="border-t border-border" />

              {/* Comments */}
              <div className="flex flex-col gap-3">
                <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                  <CommentRegular className="w-3 h-3" />
                  Comments ({comments?.length ?? 0})
                </span>

                {comments && comments.length > 0 && (
                  <div className="space-y-3">
                    {comments.map((comment) => (
                      <div key={comment.id} className="flex gap-2.5">
                        <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <PersonRegular className="w-3.5 h-3.5 text-accent" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-baseline gap-2 mb-0.5">
                            <span className="text-xs font-medium text-text-primary">
                              {comment.author?.name ?? comment.author_id}
                            </span>
                            <span className="text-[10px] text-text-tertiary">
                              {relativeTime(comment.created_at)}
                            </span>
                          </div>
                          <p className="text-sm text-text-secondary whitespace-pre-wrap">
                            {comment.content}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Comment input */}
                <div className="flex gap-2 mt-1">
                  <textarea
                    value={commentValue}
                    onChange={(e) => setCommentValue(e.target.value)}
                    placeholder="Write a comment..."
                    rows={2}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        submitComment()
                      }
                    }}
                    className="
                      flex-1 bg-bg-tertiary border border-border rounded px-3 py-2
                      text-sm text-text-primary resize-none placeholder:text-text-tertiary
                      focus:outline-none focus:border-accent/60 transition-colors
                    "
                  />
                  <button
                    onClick={submitComment}
                    disabled={!commentValue.trim() || createComment.isPending}
                    className="
                      w-8 h-8 self-end rounded flex items-center justify-center
                      bg-accent text-white
                      hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed
                      transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
                    "
                    aria-label="Send comment"
                  >
                    <SendRegular className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-[10px] text-text-tertiary">
                  Cmd/Ctrl + Enter to submit
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
