import { useQuery } from '@tanstack/react-query'
import { dashboardApi, type DashboardData } from '../api/dashboard'

export const dashboardKeys = {
  detail: (projectId: string) => ['dashboard', projectId] as const,
}

/**
 * Fetch and auto-refresh project dashboard analytics every 60 seconds.
 */
export function useDashboard(projectId: string) {
  return useQuery<DashboardData>({
    queryKey: dashboardKeys.detail(projectId),
    queryFn: () => dashboardApi.get(projectId),
    enabled: !!projectId,
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  })
}
