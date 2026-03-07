import apiClient from './client'

export interface Team {
  id: string
  name: string
  description?: string
  key: string
  created_at: string
}

export interface Project {
  id: string
  name: string
  key: string
  description?: string
  team_id: string
  created_at: string
}

export interface SetupStatus {
  is_initialized: boolean
}

export interface SetupInitPayload {
  admin_email: string
  admin_password: string
  admin_name: string
  app_name?: string
  google_client_id?: string
  google_client_secret?: string
  google_redirect_uri?: string
}

export interface CreateTeamPayload {
  name: string
  description?: string
}

export interface CreateProjectPayload {
  name: string
  key: string
  description?: string
}

export const setupApi = {
  /** Check if the server has been initialized */
  getStatus: () => apiClient.get<SetupStatus>('/setup/status').then((r) => r.data),

  /** Initialize the server with admin account */
  init: (payload: SetupInitPayload) =>
    apiClient.post('/setup/init', payload).then((r) => r.data),
}

export const teamsApi = {
  /** List all teams the current user belongs to */
  list: () => apiClient.get<Team[]>('/teams').then((r) => r.data),

  /** Create a new team */
  create: (payload: CreateTeamPayload) =>
    apiClient.post<Team>('/teams', payload).then((r) => r.data),

  /** List projects for a specific team */
  listProjects: (teamId: string) =>
    apiClient.get<Project[]>(`/teams/${teamId}/projects`).then((r) => r.data),

  /** Create a project under a team */
  createProject: (teamId: string, payload: CreateProjectPayload) =>
    apiClient.post<Project>(`/teams/${teamId}/projects`, payload).then((r) => r.data),
}
