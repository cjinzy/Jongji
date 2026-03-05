/**
 * Task domain types for Jongji project management.
 */

export type TaskStatus =
  | 'BACKLOG'
  | 'TODO'
  | 'PROGRESS'
  | 'REVIEW'
  | 'DONE'
  | 'REOPEN'
  | 'CLOSED'

/** 0=none, 1=low, 2=medium, 3=high, 4=urgent */
export type TaskPriority = 0 | 1 | 2 | 3 | 4

export interface Label {
  id: string
  name: string
  color: string
}

export interface Tag {
  id: string
  name: string
}

export interface Task {
  id: string
  project_id: string
  number: number
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  creator_id: string
  assignee_id: string | null
  start_date: string | null
  due_date: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
  labels: Label[]
  tags: Tag[]
  /** Project short key (e.g. "JNG") — populated in detail responses */
  project_key?: string
}

export interface TasksPage {
  items: Task[]
  next_cursor: string | null
  has_more: boolean
}

export interface CreateTaskPayload {
  title: string
  description?: string
  status?: TaskStatus
  priority?: TaskPriority
  assignee_id?: string
  start_date?: string
  due_date?: string
}

export interface UpdateTaskPayload {
  title?: string
  description?: string
  priority?: TaskPriority
  assignee_id?: string | null
  start_date?: string | null
  due_date?: string | null
}

export interface UpdateTaskStatusPayload {
  status: TaskStatus
}

export interface Comment {
  id: string
  task_id: string
  author_id: string
  content: string
  created_at: string
  updated_at: string
  author?: {
    id: string
    name: string
    email: string
  }
}

export interface CreateCommentPayload {
  content: string
}

export const TASK_STATUSES: TaskStatus[] = [
  'BACKLOG',
  'TODO',
  'PROGRESS',
  'REVIEW',
  'DONE',
  'REOPEN',
  'CLOSED',
]

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  0: 'None',
  1: 'Low',
  2: 'Medium',
  3: 'High',
  4: 'Urgent',
}
