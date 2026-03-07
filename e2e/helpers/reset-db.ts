import { BACKEND_URL, API_PREFIX } from './constants'

/**
 * Resets the test database via the backend test utility endpoint.
 * Requires the backend to expose POST /api/v1/test/reset-db.
 */
export async function resetDb(): Promise<void> {
  const url = `${BACKEND_URL}${API_PREFIX}/test/reset-db`
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) {
    const body = await res.text().catch(() => '(no body)')
    throw new Error(`resetDb failed: ${res.status} ${res.statusText} — ${body}`)
  }
}
