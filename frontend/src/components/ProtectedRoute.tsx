import { Navigate, Outlet } from 'react-router'
import { useAuth } from '../hooks/useAuth'

/**
 * Route guard — redirects unauthenticated users to /login.
 * Shows nothing while the session check is in flight.
 */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
