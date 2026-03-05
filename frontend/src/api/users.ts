import apiClient from './client'

export interface User {
  id: string
  name: string
  email: string
  avatar_url?: string
}

/**
 * Search users by name or email for mention autocomplete.
 */
export const usersApi = {
  search: async (query: string): Promise<User[]> => {
    const res = await apiClient.get<User[]>('/users', {
      params: { q: query },
    })
    return res.data
  },
}
