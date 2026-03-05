import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listTasksApi,
  getTaskApi,
  updateTaskApi,
  updateTaskStatusApi,
  createTaskApi,
  listCommentsApi,
  createCommentApi,
  type ListTasksParams,
} from '../api/tasks'
import type {
  Task,
  TaskStatus,
  UpdateTaskPayload,
  CreateTaskPayload,
  CreateCommentPayload,
} from '../types/task'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const taskKeys = {
  all: (projectId: string) => ['tasks', projectId] as const,
  list: (projectId: string, params?: ListTasksParams) =>
    ['tasks', projectId, 'list', params] as const,
  detail: (taskId: string) => ['tasks', 'detail', taskId] as const,
  comments: (taskId: string) => ['tasks', 'comments', taskId] as const,
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all tasks for a project grouped by status.
 * Returns a map of status -> Task[] for easy kanban rendering.
 */
export function useProjectTasks(projectId: string, params?: ListTasksParams) {
  return useQuery({
    queryKey: taskKeys.list(projectId, params),
    queryFn: () => listTasksApi(projectId, params),
    enabled: !!projectId,
    staleTime: 30 * 1000,
  })
}

/**
 * Fetch task detail.
 */
export function useTask(taskId: string | null) {
  return useQuery({
    queryKey: taskKeys.detail(taskId ?? ''),
    queryFn: () => getTaskApi(taskId!),
    enabled: !!taskId,
    staleTime: 30 * 1000,
  })
}

/**
 * Fetch comments for a task.
 */
export function useTaskComments(taskId: string | null) {
  return useQuery({
    queryKey: taskKeys.comments(taskId ?? ''),
    queryFn: () => listCommentsApi(taskId!),
    enabled: !!taskId,
    staleTime: 10 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Optimistic status update with automatic rollback on failure.
 */
export function useUpdateTaskStatus(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      taskId,
      status,
    }: {
      taskId: string
      status: TaskStatus
    }) => updateTaskStatusApi(taskId, { status }),

    onMutate: async ({ taskId, status }) => {
      // Cancel in-flight queries to avoid overwriting our optimistic update
      await queryClient.cancelQueries({ queryKey: taskKeys.all(projectId) })

      const previousData = queryClient.getQueryData(taskKeys.list(projectId))

      // Optimistically update the cached task list
      queryClient.setQueryData(
        taskKeys.list(projectId),
        (old: { items: Task[] } | undefined) => {
          if (!old) return old
          return {
            ...old,
            items: old.items.map((t) =>
              t.id === taskId ? { ...t, status } : t,
            ),
          }
        },
      )

      return { previousData }
    },

    onError: (_err, _vars, context) => {
      // Roll back to the snapshot taken before the optimistic update
      if (context?.previousData) {
        queryClient.setQueryData(taskKeys.list(projectId), context.previousData)
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all(projectId) })
    },
  })
}

/**
 * Update task fields (title, description, priority, etc.).
 */
export function useUpdateTask(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      taskId,
      payload,
    }: {
      taskId: string
      payload: UpdateTaskPayload
    }) => updateTaskApi(taskId, payload),

    onSuccess: (updatedTask) => {
      queryClient.setQueryData(taskKeys.detail(updatedTask.id), updatedTask)
      queryClient.invalidateQueries({ queryKey: taskKeys.all(projectId) })
    },
  })
}

/**
 * Create a new task.
 */
export function useCreateTask(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateTaskPayload) =>
      createTaskApi(projectId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all(projectId) })
    },
  })
}

/**
 * Post a comment on a task.
 */
export function useCreateComment(taskId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateCommentPayload) =>
      createCommentApi(taskId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.comments(taskId) })
    },
  })
}
