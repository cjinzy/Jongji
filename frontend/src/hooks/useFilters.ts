import {
  parseAsArrayOf,
  parseAsString,
  parseAsBoolean,
  parseAsInteger,
  useQueryStates,
} from 'nuqs'
import type { TaskStatus, TaskPriority } from '../types/task'

/**
 * URL-synced filter state shared between Kanban and Table views.
 * Uses nuqs to keep filters in the query string so they survive navigation.
 *
 * Example URL:
 *   ?status=TODO,PROGRESS&assignee=me&priority=1,2,3&unassigned=true
 */
export const filterParsers = {
  status: parseAsArrayOf(parseAsString).withDefault([]),
  assignee: parseAsString.withDefault(''),
  priority: parseAsArrayOf(parseAsInteger).withDefault([]),
  unassigned: parseAsBoolean.withDefault(false),
}

export type FilterState = {
  status: TaskStatus[]
  assignee: string
  priority: TaskPriority[]
  unassigned: boolean
}

/**
 * Returns nuqs-backed filter state + setters.
 * Must be used inside a NuqsAdapter context (set up in App.tsx).
 */
export function useFilters() {
  const [filters, setFilters] = useQueryStates(filterParsers, {
    history: 'push',
    shallow: true,
  })

  return {
    filters: filters as FilterState,
    setFilters,
    resetFilters: () =>
      setFilters({ status: [], assignee: '', priority: [], unassigned: false }),
    hasActiveFilters:
      filters.status.length > 0 ||
      filters.assignee !== '' ||
      filters.priority.length > 0 ||
      filters.unassigned,
  }
}
