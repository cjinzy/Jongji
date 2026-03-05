import apiClient from './client'

export interface Session {
  id: string
  user_agent: string
  ip_address: string
  last_active_at: string
  created_at: string
  is_current: boolean
}

/**
 * Fetch all active sessions for the current user.
 */
export async function getSessions(): Promise<Session[]> {
  const res = await apiClient.get<Session[]>('/sessions')
  return res.data
}

/**
 * Revoke (logout) a specific session by ID.
 */
export async function revokeSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}`)
}
