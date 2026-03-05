import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/auth'
import { getMeApi } from '../api/auth'

/**
 * Auth hook that syncs TanStack Query user data with the Zustand auth store.
 * Fetches /users/me when a token is present and keeps the store up to date.
 */
export function useAuth() {
  const { user, token, isAuthenticated, login, logout, setUser } = useAuthStore()

  const { isLoading, error } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const me = await getMeApi()
      setUser(me)
      return me
    },
    enabled: !!token && !user,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  return {
    user,
    token,
    isAuthenticated,
    isLoading: isLoading && !!token,
    error,
    login,
    logout,
  }
}
