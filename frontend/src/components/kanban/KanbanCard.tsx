import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  LockClosedRegular,
  PersonRegular,
  AlertUrgentRegular,
  ArrowUpRegular,
  SubtractCircleRegular,
  ArrowDownRegular,
  LineHorizontal3Regular,
} from '@fluentui/react-icons'
import type { Task, TaskPriority } from '../../types/task'

interface KanbanCardProps {
  task: Task
  isBlocked?: boolean
  onClick: (task: Task) => void
}

const priorityConfig: Record<
  TaskPriority,
  { icon: React.ReactNode; className: string; label: string }
> = {
  0: {
    icon: <LineHorizontal3Regular className="w-3.5 h-3.5" />,
    className: 'text-text-tertiary',
    label: 'None',
  },
  1: {
    icon: <ArrowDownRegular className="w-3.5 h-3.5" />,
    className: 'text-success',
    label: 'Low',
  },
  2: {
    icon: <SubtractCircleRegular className="w-3.5 h-3.5" />,
    className: 'text-warning',
    label: 'Medium',
  },
  3: {
    icon: <ArrowUpRegular className="w-3.5 h-3.5" />,
    className: 'text-danger',
    label: 'High',
  },
  4: {
    icon: <AlertUrgentRegular className="w-3.5 h-3.5" />,
    className: 'text-danger',
    label: 'Urgent',
  },
}

/** Derive initials from a user name or id string */
function getInitials(nameOrId: string): string {
  const parts = nameOrId.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return nameOrId.slice(0, 2).toUpperCase()
}

/** Deterministic hue from an id string for avatar background */
function idToHue(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) & 0xffffffff
  }
  return Math.abs(hash) % 360
}

export function KanbanCard({ task, isBlocked = false, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    cursor: isDragging ? 'grabbing' : 'grab',
  }

  const priority = priorityConfig[task.priority]
  const hue = task.assignee_id ? idToHue(task.assignee_id) : 0

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onClick(task)}
      className="
        group relative
        bg-bg-secondary border border-border rounded-md px-3 py-2.5
        hover:border-accent/40 hover:bg-bg-tertiary
        transition-colors duration-150 select-none
        focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
      "
      aria-label={`Task ${task.project_key ?? ''}#${task.number}: ${task.title}`}
    >
      {/* Blocked indicator */}
      {isBlocked && (
        <span
          className="
            absolute -top-1.5 -right-1.5
            bg-danger text-white rounded-full w-4 h-4
            flex items-center justify-center shadow
          "
          title="Blocked by another task"
        >
          <LockClosedRegular className="w-2.5 h-2.5" />
        </span>
      )}

      {/* Project key + number */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono text-text-tertiary tracking-wide">
          {task.project_key ?? 'JNG'}-{task.number}
        </span>
        {/* Priority icon */}
        <span className={priority.className} title={priority.label}>
          {priority.icon}
        </span>
      </div>

      {/* Title */}
      <p className="text-sm text-text-primary leading-snug line-clamp-2 mb-2">
        {task.title}
      </p>

      {/* Footer: labels + assignee avatar */}
      <div className="flex items-center justify-between gap-2">
        {/* Labels (first 2) */}
        <div className="flex items-center gap-1 min-w-0 flex-1">
          {task.labels.slice(0, 2).map((label) => (
            <span
              key={label.id}
              className="text-[10px] px-1.5 py-0.5 rounded-full font-medium truncate"
              style={{
                backgroundColor: label.color + '33',
                color: label.color,
                border: `1px solid ${label.color}55`,
              }}
            >
              {label.name}
            </span>
          ))}
        </div>

        {/* Assignee avatar */}
        {task.assignee_id ? (
          <div
            className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-bold text-white"
            style={{ backgroundColor: `hsl(${hue}, 55%, 42%)` }}
            title={`Assignee: ${task.assignee_id}`}
          >
            {getInitials(task.assignee_id)}
          </div>
        ) : (
          <div
            className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center bg-bg-hover"
            title="Unassigned"
          >
            <PersonRegular className="w-3 h-3 text-text-tertiary" />
          </div>
        )}
      </div>
    </div>
  )
}
