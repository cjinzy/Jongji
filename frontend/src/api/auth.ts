import apiClient from './client'
import type { User } from '../stores/auth'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
}

/**
 * Authenticate user with email and password.
 */
export async function loginApi(data: LoginRequest): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>('/auth/login', data)
  return res.data
}

/**
 * Register a new user account.
 */
export async function registerApi(data: RegisterRequest): Promise<User> {
  const res = await apiClient.post<User>('/auth/register', data)
  return res.data
}

/**
 * Invalidate the current session on the server.
 */
export async function logoutApi(): Promise<void> {
  await apiClient.post('/auth/logout')
}

/**
 * Fetch the currently authenticated user's profile.
 */
export async function getMeApi(): Promise<User> {
  const res = await apiClient.get<User>('/users/me')
  return res.data
}
