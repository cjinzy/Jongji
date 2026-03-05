import apiClient from './client'

export interface DashboardData {
  status_counts: Record<string, number>
  priority_distribution: { priority: number; count: number }[]
  assignee_workload: { user_id: string; user_name: string; count: number }[]
  daily_created: { date: string; count: number }[]
  daily_completed: { date: string; count: number }[]
  label_distribution: {
    label_id: string
    label_name: string
    color: string
    count: number
  }[]
  total_tasks: number
  completed_tasks: number
  completion_rate: number
}

/**
 * Fetch dashboard analytics data for a project.
 */
export const dashboardApi = {
  get: async (projectId: string): Promise<DashboardData> => {
    const res = await apiClient.get<DashboardData>(
      `/projects/${projectId}/dashboard`,
    )
    return res.data
  },
}
