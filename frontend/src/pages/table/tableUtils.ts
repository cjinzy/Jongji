import type { Task } from '../../types/task'
import { TASK_STATUSES } from '../../types/task'

/** Column keys that the table can be sorted by. */
export type SortKey = 'number' | 'title' | 'status' | 'priority' | 'due_date' | 'created_at'

/** Sort direction. */
export type SortDir = 'asc' | 'desc'

/**
 * Returns a sorted copy of the given task array.
 * Comparison is stable for equal values.
 */
export function sortTasks(tasks: Task[], key: SortKey, dir: SortDir): Task[] {
  return [...tasks].sort((a, b) => {
    let cmp = 0
    if (key === 'number') {
      cmp = a.number - b.number
    } else if (key === 'title') {
      cmp = a.title.localeCompare(b.title)
    } else if (key === 'status') {
      cmp = TASK_STATUSES.indexOf(a.status) - TASK_STATUSES.indexOf(b.status)
    } else if (key === 'priority') {
      cmp = a.priority - b.priority
    } else if (key === 'due_date') {
      const ad = a.due_date ?? ''
      const bd = b.due_date ?? ''
      cmp = ad < bd ? -1 : ad > bd ? 1 : 0
    } else if (key === 'created_at') {
      cmp = a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0
    }
    return dir === 'asc' ? cmp : -cmp
  })
}
