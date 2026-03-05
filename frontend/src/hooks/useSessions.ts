import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSessions, revokeSession } from '../api/sessions'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const sessionKeys = {
  all: ['sessions'] as const,
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all active sessions for the current user.
 */
export function useSessions() {
  return useQuery({
    queryKey: sessionKeys.all,
    queryFn: getSessions,
    staleTime: 30 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Revoke a specific session by ID and refetch the session list.
 */
export function useRevokeSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}
