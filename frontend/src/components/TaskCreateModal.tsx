import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { DismissRegular } from '@fluentui/react-icons'
import { useCreateTask } from '../hooks/useTasks'
import type { TaskStatus, TaskPriority } from '../types/task'
import { TASK_STATUSES } from '../types/task'
import { STATUS_LABELS, PRIORITY_LABELS } from '../constants/task'

interface TaskCreateModalProps {
  projectId: string
  defaultStatus?: TaskStatus
  isOpen: boolean
  onClose: () => void
  onCreated?: () => void
}

export function TaskCreateModal({
  projectId,
  defaultStatus = 'TODO',
  isOpen,
  onClose,
  onCreated,
}: TaskCreateModalProps) {
  const { t } = useTranslation()
  const titleRef = useRef<HTMLInputElement>(null)
  const createTask = useCreateTask(projectId)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState<TaskStatus>(defaultStatus)
  const [priority, setPriority] = useState<TaskPriority>(0)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle('')
      setDescription('')
      setStatus(defaultStatus)
      setPriority(0)
      // Autofocus title
      setTimeout(() => titleRef.current?.focus(), 50)
    }
  }, [isOpen, defaultStatus])

  // Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return

    createTask.mutate(
      {
        title: title.trim(),
        description: description.trim() || undefined,
        status,
        priority,
      },
      {
        onSuccess: () => {
          onCreated?.()
          onClose()
        },
      },
    )
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
        role="presentation"
      >
        {/* Modal */}
        <div
          className="
            w-full max-w-md bg-bg-secondary border border-border rounded-xl shadow-2xl
            animate-in fade-in slide-in-from-bottom-2 duration-200
          "
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label={t('task.create')}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-border">
            <h3 className="text-sm font-semibold text-text-primary">
              {t('task.create')}
            </h3>
            <button
              onClick={onClose}
              className="
                w-6 h-6 rounded flex items-center justify-center
                text-text-tertiary hover:text-text-primary hover:bg-bg-hover
                transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
              "
              aria-label={t('common.cancel')}
            >
              <DismissRegular className="w-4 h-4" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
            {/* Title */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-text-tertiary uppercase tracking-wide">
                {t('task.title')} *
              </label>
              <input
                ref={titleRef}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Task title..."
                required
                className="
                  bg-bg-tertiary border border-border rounded px-3 py-2
                  text-sm text-text-primary placeholder:text-text-tertiary
                  focus:outline-none focus:border-accent/60 transition-colors
                "
              />
            </div>

            {/* Description */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-text-tertiary uppercase tracking-wide">
                {t('task.description')}
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description..."
                rows={3}
                className="
                  bg-bg-tertiary border border-border rounded px-3 py-2
                  text-sm text-text-primary placeholder:text-text-tertiary resize-none
                  focus:outline-none focus:border-accent/60 transition-colors
                "
              />
            </div>

            {/* Status + Priority row */}
            <div className="flex gap-3">
              <div className="flex flex-col gap-1.5 flex-1">
                <label className="text-[10px] text-text-tertiary uppercase tracking-wide">
                  {t('task.status')}
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value as TaskStatus)}
                  className="
                    bg-bg-tertiary border border-border rounded px-2 py-1.5
                    text-xs text-text-primary focus:outline-none focus:border-accent/60
                    cursor-pointer
                  "
                >
                  {TASK_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABELS[s]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5 flex-1">
                <label className="text-[10px] text-text-tertiary uppercase tracking-wide">
                  {t('task.priority')}
                </label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value) as TaskPriority)}
                  className="
                    bg-bg-tertiary border border-border rounded px-2 py-1.5
                    text-xs text-text-primary focus:outline-none focus:border-accent/60
                    cursor-pointer
                  "
                >
                  {([0, 1, 2, 3, 4] as TaskPriority[]).map((p) => (
                    <option key={p} value={p}>
                      {PRIORITY_LABELS[p]}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="
                  text-xs px-4 py-1.5 rounded bg-bg-hover text-text-secondary
                  hover:text-text-primary transition-colors
                  focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
                "
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={!title.trim() || createTask.isPending}
                className="
                  text-xs px-4 py-1.5 rounded bg-accent text-white font-medium
                  hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed
                  transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
                "
              >
                {createTask.isPending ? t('common.loading') : t('task.create')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
