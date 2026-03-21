import { Navigate, Outlet } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import apiClient from '../api/client'

/**
 * Route guard — checks setup status first, then auth.
 * Setup incomplete → /setup, unauthenticated → /login.
 * When AUTH_DISABLED, allows access without authentication.
 */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading, authDisabled } = useAuth()

  const { data: setupStatus, isLoading: isSetupLoading } = useQuery({
    queryKey: ['setup-status'],
    queryFn: async () => {
      const res = await apiClient.get<{ setup_completed: boolean }>('/setup/status')
      return res.data
    },
    staleTime: Infinity,
    retry: false,
  })

  if (isLoading || isSetupLoading) {
    return null
  }

  if (setupStatus && !setupStatus.setup_completed) {
    return <Navigate to="/setup" replace />
  }

  if (!isAuthenticated && !authDisabled) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
