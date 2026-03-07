import { BACKEND_URL, API_PREFIX } from './constants'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SetupInitPayload {
  admin_name: string
  admin_email: string
  admin_password: string
  app_name: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  /** Raw Set-Cookie header strings */
  cookies: string[]
}

export interface Team {
  id: string
  name: string
  description?: string
  key?: string
}

export interface Project {
  id: string
  name: string
  key: string
  description?: string
  team_id: string
}

export interface Task {
  id: string
  title: string
  description?: string
  status: string
  priority: number
  project_id: string
}

// ---------------------------------------------------------------------------
// Helper: build base URL
// ---------------------------------------------------------------------------

function url(path: string): string {
  return `${BACKEND_URL}${API_PREFIX}${path}`
}

// ---------------------------------------------------------------------------
// Helper: assert response is OK
// ---------------------------------------------------------------------------

async function assertOk(res: Response, label: string): Promise<void> {
  if (!res.ok) {
    const body = await res.text().catch(() => '(no body)')
    throw new Error(`[api.ts] ${label} failed: ${res.status} ${res.statusText} — ${body}`)
  }
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

/**
 * Calls the one-time setup wizard endpoint to initialise the app.
 */
export async function setupInit(data: SetupInitPayload): Promise<void> {
  const res = await fetch(url('/setup/init'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  await assertOk(res, 'setupInit')
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/**
 * Logs in via the backend directly (bypasses nginx).
 * Returns the access token and any Set-Cookie headers for session use.
 */
export async function login(email: string, password: string): Promise<LoginResult> {
  const res = await fetch(url('/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  await assertOk(res, 'login')

  const data = await res.json()
  const setCookieHeader = res.headers.get('set-cookie')
  const cookies: string[] = setCookieHeader
    ? setCookieHeader.split(/,(?=\s*\w+=)/).map((c) => c.trim())
    : []

  return {
    access_token: data.access_token as string,
    token_type: data.token_type as string,
    cookies,
  }
}

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

/**
 * Creates a team. Requires a valid access token.
 */
export async function createTeam(
  token: string,
  data: { name: string; description?: string },
): Promise<Team> {
  const res = await fetch(url('/teams'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
  await assertOk(res, 'createTeam')
  return res.json() as Promise<Team>
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

/**
 * Creates a project under a team. Requires a valid access token.
 */
export async function createProject(
  token: string,
  teamId: string,
  data: { name: string; key: string; description?: string },
): Promise<Project> {
  const res = await fetch(url(`/teams/${teamId}/projects`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
  await assertOk(res, 'createProject')
  return res.json() as Promise<Project>
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

/**
 * Creates a task. Requires a valid access token.
 */
export async function createTask(
  token: string,
  data: {
    project_id: string
    title: string
    description?: string
    status?: string
    priority?: number
  },
): Promise<Task> {
  const res = await fetch(url('/tasks'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      status: 'TODO',
      priority: 0,
      ...data,
    }),
  })
  await assertOk(res, 'createTask')
  return res.json() as Promise<Task>
}
