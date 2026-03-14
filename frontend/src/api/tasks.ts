import apiClient from './client'
import type {
  Task,
  TasksPage,
  CreateTaskPayload,
  UpdateTaskPayload,
  UpdateTaskStatusPayload,
  Comment,
  CreateCommentPayload,
} from '../types/task'

export interface ListTasksParams {
  status?: string
  assignee_id?: string
  priority?: number
  is_archived?: boolean
  cursor?: string
  limit?: number
}

/**
 * Fetch paginated task list for a project.
 */
export async function listTasksApi(
  projectId: string,
  params?: ListTasksParams,
): Promise<TasksPage> {
  const res = await apiClient.get<TasksPage>(`/projects/${projectId}/tasks`, {
    params: { is_archived: false, limit: 50, ...params },
  })
  return res.data
}

/**
 * Fetch a single task with full detail (labels, tags, project).
 */
export async function getTaskApi(taskId: string): Promise<Task> {
  const res = await apiClient.get<Task>(`/tasks/${taskId}`)
  return res.data
}

/**
 * Fetch a task by project-scoped task number (human-readable sequential number).
 * Preferred over getTaskApi for URL-based navigation where only the task number is known.
 */
export async function getTaskByNumberApi(
  projectId: string,
  taskNumber: number,
): Promise<Task> {
  const res = await apiClient.get<Task>(
    `/projects/${projectId}/tasks/by-number/${taskNumber}`,
  )
  return res.data
}

/**
 * Update task fields (title, description, priority, assignee, dates).
 */
export async function updateTaskApi(
  taskId: string,
  payload: UpdateTaskPayload,
): Promise<Task> {
  const res = await apiClient.put<Task>(`/tasks/${taskId}`, payload)
  return res.data
}

/**
 * Transition task status. Server validates blocked_by constraints.
 */
export async function updateTaskStatusApi(
  taskId: string,
  payload: UpdateTaskStatusPayload,
): Promise<Task> {
  const res = await apiClient.patch<Task>(`/tasks/${taskId}/status`, payload)
  return res.data
}

/**
 * Create a new task in a project.
 */
export async function createTaskApi(
  projectId: string,
  payload: CreateTaskPayload,
): Promise<Task> {
  const res = await apiClient.post<Task>(`/projects/${projectId}/tasks`, payload)
  return res.data
}

/**
 * Fetch all comments for a task.
 */
export async function listCommentsApi(taskId: string): Promise<Comment[]> {
  const res = await apiClient.get<Comment[]>(`/tasks/${taskId}/comments`)
  return res.data
}

/**
 * Post a new comment on a task.
 */
export async function createCommentApi(
  taskId: string,
  payload: CreateCommentPayload,
): Promise<Comment> {
  const res = await apiClient.post<Comment>(`/tasks/${taskId}/comments`, payload)
  return res.data
}
