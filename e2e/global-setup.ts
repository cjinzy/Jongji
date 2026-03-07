import { chromium } from '@playwright/test'

const HEALTH_URL = 'http://localhost:3100/api/v1/health'
const READY_URL = 'http://localhost:3100/api/v1/ready'
const MAX_WAIT_MS = 60_000
const INTERVAL_MS = 2_000

async function waitForUrl(url: string, label: string): Promise<void> {
  const deadline = Date.now() + MAX_WAIT_MS
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url)
      if (res.ok) {
        console.log(`[global-setup] ${label} OK`)
        return
      }
      console.log(`[global-setup] ${label} responded ${res.status}, retrying...`)
    } catch {
      console.log(`[global-setup] ${label} not reachable yet, retrying...`)
    }
    await new Promise((r) => setTimeout(r, INTERVAL_MS))
  }
  throw new Error(`[global-setup] Timed out waiting for ${label} at ${url}`)
}

async function globalSetup(): Promise<void> {
  console.log('[global-setup] Waiting for backend to be healthy...')
  await waitForUrl(HEALTH_URL, 'health')
  await waitForUrl(READY_URL, 'ready')
  console.log('[global-setup] Backend is ready.')

  // Verify Playwright browser binary is available
  const browser = await chromium.launch()
  await browser.close()
}

export default globalSetup
