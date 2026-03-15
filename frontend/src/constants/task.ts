/**
 * Task domain constants — status/priority labels, colors, and metadata.
 *
 * Single source of truth for all task-related display constants.
 * Import from here instead of defining locally in each component.
 */

import type { TaskStatus, TaskPriority } from '../types/task'

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

export const STATUS_LABELS: Record<TaskStatus, string> = {
  BACKLOG: 'Backlog',
  TODO: 'Todo',
  PROGRESS: 'In Progress',
  REVIEW: 'In Review',
  DONE: 'Done',
  REOPEN: 'Reopened',
  CLOSED: 'Closed',
}

export const STATUS_COLORS: Record<TaskStatus, string> = {
  BACKLOG: '#6B6B76',
  TODO: '#5B6AF0',
  PROGRESS: '#F59E0B',
  REVIEW: '#8B5CF6',
  DONE: '#22C55E',
  REOPEN: '#EF4444',
  CLOSED: '#374151',
}

export interface StatusMeta {
  label: string
  color: string
}

export const STATUS_META: Record<TaskStatus, StatusMeta> = Object.fromEntries(
  (Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => [
    s,
    { label: STATUS_LABELS[s], color: STATUS_COLORS[s] },
  ]),
) as Record<TaskStatus, StatusMeta>

// ---------------------------------------------------------------------------
// Priority
// Priority values in the frontend use 0-4 scale:
//   0=None, 1=Low, 2=Medium, 3=High, 4=Urgent
// Note: backend uses 1-9 scale; the API layer maps between them.
// ---------------------------------------------------------------------------

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  0: 'None',
  1: 'Low',
  2: 'Medium',
  3: 'High',
  4: 'Urgent',
}

export const PRIORITY_COLORS: Record<TaskPriority, string> = {
  0: '#6B7280',
  1: '#5B6AF0',
  2: '#F59E0B',
  3: '#F97316',
  4: '#EF4444',
}

export interface PriorityMeta {
  label: string
  color: string
}

export const PRIORITY_META: Record<TaskPriority, PriorityMeta> = Object.fromEntries(
  ([0, 1, 2, 3, 4] as TaskPriority[]).map((p) => [
    p,
    { label: PRIORITY_LABELS[p], color: PRIORITY_COLORS[p] },
  ]),
) as Record<TaskPriority, PriorityMeta>

// ---------------------------------------------------------------------------
// Chart palette (used in dashboard)
// ---------------------------------------------------------------------------

export const CHART_COLORS = [
  '#5B6AF0',
  '#22C55E',
  '#F59E0B',
  '#8B5CF6',
  '#EF4444',
  '#06B6D4',
  '#EC4899',
  '#F97316',
]
