import apiClient from './client'

export interface GoogleOAuthSettings {
  client_id: string
  redirect_uri: string
  secret_masked: string
}

export interface GoogleOAuthSettingsUpdate {
  client_id: string
  client_secret: string
  redirect_uri: string
}

export const adminApi = {
  /** Fetch Google OAuth configuration */
  getGoogleOAuth: () =>
    apiClient.get<GoogleOAuthSettings>('/admin/oauth/google').then((r) => r.data),

  /** Create or update Google OAuth configuration */
  updateGoogleOAuth: (payload: GoogleOAuthSettingsUpdate) =>
    apiClient.put<GoogleOAuthSettings>('/admin/oauth/google', payload).then((r) => r.data),

  /** Delete Google OAuth configuration */
  deleteGoogleOAuth: () => apiClient.delete('/admin/oauth/google').then((r) => r.data),
}
