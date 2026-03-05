import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { AddRegular } from '@fluentui/react-icons'
import { KanbanCard } from './KanbanCard'
import type { Task, TaskStatus } from '../../types/task'

interface KanbanColumnProps {
  status: TaskStatus
  label: string
  tasks: Task[]
  accentColor: string
  onCardClick: (task: Task) => void
  onAddTask: (status: TaskStatus) => void
}

export function KanbanColumn({
  status,
  label,
  tasks,
  accentColor,
  onCardClick,
  onAddTask,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div className="flex flex-col w-[220px] flex-shrink-0">
      {/* Column header */}
      <div className="flex items-center gap-2 mb-2 px-1">
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: accentColor }}
        />
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-widest flex-1 truncate">
          {label}
        </span>
        <span className="text-xs text-text-tertiary font-mono tabular-nums">
          {tasks.length}
        </span>
        <button
          onClick={() => onAddTask(status)}
          className="
            w-5 h-5 rounded flex items-center justify-center
            text-text-tertiary hover:text-text-primary hover:bg-bg-hover
            transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
          "
          aria-label={`Add task to ${label}`}
        >
          <AddRegular className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={`
          flex flex-col gap-2 min-h-[120px] rounded-lg p-1.5
          transition-colors duration-150
          ${isOver ? 'bg-accent/8 ring-1 ring-accent/30' : 'bg-bg-primary/40'}
        `}
      >
        <SortableContext
          items={tasks.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {tasks.map((task) => (
            <KanbanCard
              key={task.id}
              task={task}
              isBlocked={false}
              onClick={onCardClick}
            />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-[11px] text-text-tertiary">Empty</span>
          </div>
        )}
      </div>
    </div>
  )
}
