import { useEffect, useRef } from 'react'
import Gantt, { type FrappeGanttTask } from 'frappe-gantt'
import 'frappe-gantt/dist/frappe-gantt.css'
import './gantt-dark.css'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GanttTask {
  id: string
  name: string
  start: string // YYYY-MM-DD
  end: string   // YYYY-MM-DD
  progress: number // 0-100
  dependencies?: string // comma-separated task ids
  custom_class?: string
}

export type ViewMode = 'Day' | 'Week' | 'Month'

interface GanttChartProps {
  tasks: GanttTask[]
  viewMode?: ViewMode
  onTaskClick?: (task: GanttTask) => void
  onDateChange?: (task: GanttTask, start: Date, end: Date) => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Wrapper around frappe-gantt that integrates with the app's dark theme.
 * Uses useRef to manage the DOM-manipulating Gantt instance lifecycle.
 */
export default function GanttChart({
  tasks,
  viewMode = 'Week',
  onTaskClick,
  onDateChange,
}: GanttChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  // Store the Gantt instance — typed as any since frappe-gantt lacks TS declarations
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ganttRef = useRef<any>(null)
  const onTaskClickRef = useRef(onTaskClick)
  const onDateChangeRef = useRef(onDateChange)

  // Keep callback refs stable so the Gantt instance doesn't need to be rebuilt
  onTaskClickRef.current = onTaskClick
  onDateChangeRef.current = onDateChange

  // Build / rebuild the Gantt instance when tasks change
  useEffect(() => {
    if (!containerRef.current || tasks.length === 0) return

    // Destroy previous instance before re-creating
    if (ganttRef.current) {
      try {
        ganttRef.current.clear?.()
      } catch {
        // frappe-gantt may throw on some versions — suppress silently
      }
      // Remove leftover SVG nodes that frappe-gantt injects
      while (containerRef.current.firstChild) {
        containerRef.current.removeChild(containerRef.current.firstChild)
      }
    }

    ganttRef.current = new Gantt(containerRef.current, tasks as FrappeGanttTask[], {
      header_height: 50,
      column_width: 30,
      step: 24,
      view_modes: ['Day', 'Week', 'Month'],
      bar_height: 28,
      bar_corner_radius: 4,
      arrow_curve: 5,
      padding: 18,
      view_mode: viewMode,
      date_format: 'YYYY-MM-DD',
      popup_trigger: 'mouseover',
      language: 'en',
      on_click: (task: GanttTask) => {
        onTaskClickRef.current?.(task)
      },
      on_date_change: (task: GanttTask, start: Date, end: Date) => {
        onDateChangeRef.current?.(task, start, end)
      },
      on_progress_change: () => {
        // noop — progress editing not wired up
      },
      on_view_change: () => {
        // noop
      },
      custom_popup_html: (task: GanttTask) => {
        const progress = Math.round(task.progress)
        return `
          <div class="title">${task.name}</div>
          <div class="subtitle">
            ${task.start} &rarr; ${task.end} &nbsp;·&nbsp; ${progress}%
          </div>
        `
      },
    })

    return () => {
      // Cleanup: clear the SVG nodes
      if (ganttRef.current) {
        try {
          ganttRef.current.clear?.()
        } catch {
          // suppress
        }
        ganttRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tasks])

  // Update view mode without rebuilding the whole chart
  useEffect(() => {
    if (!ganttRef.current) return
    try {
      ganttRef.current.change_view_mode(viewMode)
    } catch {
      // suppress if instance not ready
    }
  }, [viewMode])

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-24">
        <p className="text-sm font-medium text-text-secondary">No tasks with dates</p>
        <p className="text-xs text-text-tertiary">
          Set a start date or due date on tasks to see them here.
        </p>
      </div>
    )
  }

  return (
    <div className="gantt-container w-full overflow-x-auto">
      <div ref={containerRef} />
    </div>
  )
}
