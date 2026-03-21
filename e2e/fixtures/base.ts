import { test as base, type Page } from '@playwright/test'
import { resetDb as doResetDb } from '../helpers/reset-db'
import { setupInit, login } from '../helpers/api'
import { TEST_ADMIN, TEST_APP_NAME } from '../helpers/constants'

// ---------------------------------------------------------------------------
// Fixture types
// ---------------------------------------------------------------------------

type Fixtures = {
  /** Auto-fixture: resets the DB before every test. */
  resetDb: void
  /** Fixture: ensures setup wizard has been completed via API. */
  setupComplete: void
  /** Fixture: setup + login, returns a page with auth cookies injected. */
  authenticatedPage: Page
  /** Fixture: setup + AUTH_DISABLED auto-login, no token management needed. */
  devPage: Page
}

// ---------------------------------------------------------------------------
// Extended test object
// ---------------------------------------------------------------------------

export const test = base.extend<Fixtures>({
  // ── resetDb ───────────────────────────────────────────────────────────────
  // auto: true means it runs before every test in a file that uses this fixture
  resetDb: [
    async ({}, use) => {
      await doResetDb()
      await use()
    },
    { auto: false },
  ],

  // ── setupComplete ─────────────────────────────────────────────────────────
  setupComplete: [
    async ({ resetDb: _ }, use) => {
      await setupInit({
        admin_name: TEST_ADMIN.name,
        admin_email: TEST_ADMIN.email,
        admin_password: TEST_ADMIN.password,
        app_name: TEST_APP_NAME,
      })
      await use()
    },
    { auto: false },
  ],

  // ── authenticatedPage ─────────────────────────────────────────────────────
  authenticatedPage: async ({ setupComplete: _, browser }, use) => {
    // Login via API to get cookies
    const { access_token, cookies } = await login(TEST_ADMIN.email, TEST_ADMIN.password)

    // Create a new browser context and inject cookies
    const context = await browser.newContext({
      baseURL: 'http://localhost:3100',
      extraHTTPHeaders: {
        Authorization: `Bearer ${access_token}`,
      },
    })

    // Parse and set cookies on the context (HttpOnly cookies from API)
    for (const cookieStr of cookies) {
      const parts = cookieStr.split(';').map((p) => p.trim())
      const [nameValue] = parts
      const eqIdx = nameValue.indexOf('=')
      if (eqIdx === -1) continue
      const name = nameValue.slice(0, eqIdx)
      const value = nameValue.slice(eqIdx + 1)

      await context.addCookies([
        {
          name,
          value,
          domain: 'localhost',
          path: '/',
          httpOnly: true,
          secure: false,
        },
      ])
    }

    // Store access_token and set English locale in localStorage
    const page = await context.newPage()
    await page.goto('http://localhost:3100/login')
    await page.evaluate((token: string) => {
      localStorage.setItem('access_token', token)
      localStorage.setItem('jongji-lang', 'en')
    }, access_token)

    await use(page)
    await context.close()
  },

  // ── devPage (AUTH_DISABLED mode) ──────────────────────────────────────────
  devPage: async ({ setupComplete: _, browser }, use) => {
    const context = await browser.newContext({
      baseURL: 'http://localhost:3100',
    })

    const page = await context.newPage()

    // Set English locale in localStorage
    await page.goto('http://localhost:3100/login')
    await page.evaluate(() => {
      localStorage.setItem('jongji-lang', 'en')
    })

    // Navigate to home — frontend will auto-detect AUTH_DISABLED and auto-login
    await page.goto('http://localhost:3100/')

    // Wait for auto-authentication to complete (user name appears in UI)
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 })

    await use(page)
    await context.close()
  },
})

export { expect } from '@playwright/test'
