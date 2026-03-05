/**
 * Minimal type declaration for frappe-gantt (no official @types package).
 */
declare module 'frappe-gantt' {
  export interface FrappeGanttTask {
    id: string
    name: string
    start: string
    end: string
    progress: number
    dependencies?: string
    custom_class?: string
    [key: string]: unknown
  }

  export interface FrappeGanttOptions {
    header_height?: number
    column_width?: number
    step?: number
    view_modes?: string[]
    bar_height?: number
    bar_corner_radius?: number
    arrow_curve?: number
    padding?: number
    view_mode?: string
    date_format?: string
    popup_trigger?: string
    language?: string
    on_click?: (task: FrappeGanttTask) => void
    on_date_change?: (task: FrappeGanttTask, start: Date, end: Date) => void
    on_progress_change?: (task: FrappeGanttTask, progress: number) => void
    on_view_change?: (mode: string) => void
    custom_popup_html?: (task: FrappeGanttTask) => string
  }

  export default class Gantt {
    constructor(
      wrapper: HTMLElement | string,
      tasks: FrappeGanttTask[],
      options?: FrappeGanttOptions,
    )
    change_view_mode(mode: string): void
    clear(): void
    refresh(tasks: FrappeGanttTask[]): void
  }
}
