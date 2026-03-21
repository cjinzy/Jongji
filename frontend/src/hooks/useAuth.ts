import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/auth'
import { getDevStatusApi, getMeApi } from '../api/auth'

/**
 * Auth hook that syncs TanStack Query user data with the Zustand auth store.
 * Fetches /users/me when a token is present and keeps the store up to date.
 * When AUTH_DISABLED, auto-authenticates with the dev user.
 */
export function useAuth() {
  const { user, token, isAuthenticated, login, logout, setUser, setToken } = useAuthStore()

  const { data: devStatus, isLoading: isDevStatusLoading } = useQuery({
    queryKey: ['dev-status'],
    queryFn: getDevStatusApi,
    staleTime: Infinity,
    retry: false,
  })

  const authDisabled = devStatus?.auth_disabled ?? false

  const { isLoading: isDevLoginLoading } = useQuery({
    queryKey: ['dev-auto-login'],
    queryFn: async () => {
      const me = await getMeApi()
      setUser(me)
      setToken('dev-mode')
      return me
    },
    enabled: authDisabled && !isAuthenticated,
    retry: false,
  })

  const { isLoading, error } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const me = await getMeApi()
      setUser(me)
      return me
    },
    enabled: !authDisabled && !!token && !user,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  return {
    user,
    token,
    isAuthenticated,
    isLoading: isDevStatusLoading || (authDisabled ? isDevLoginLoading && !isAuthenticated : isLoading && !!token),
    error,
    login,
    logout,
    authDisabled,
  }
}
