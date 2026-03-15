import { test, expect } from '@playwright/test'
import { resetDb } from '../helpers/reset-db'
import { TEST_ADMIN, TEST_APP_NAME } from '../helpers/constants'

test.describe('Setup Wizard', () => {
  test.beforeEach(async () => {
    await resetDb()
  })

  test('completes 3-step setup wizard and redirects to /login', async ({ page }) => {
    await page.goto('/setup')

    // ── Step 1: Admin Account ────────────────────────────────────────────────
    await expect(page.getByText('Create Admin Account')).toBeVisible()
    await expect(page.getByText('Admin Account', { exact: true })).toBeVisible()

    // Fill admin name — label text is "Admin Name" (uppercase via CSS, value is "Admin Name")
    await page.getByPlaceholder('Jane Doe').fill(TEST_ADMIN.name)
    await page.getByPlaceholder('admin@example.com').fill(TEST_ADMIN.email)
    await page.getByPlaceholder('••••••••').fill(TEST_ADMIN.password)

    // Next button
    const nextBtn = page.getByRole('button', { name: 'Next' })
    await expect(nextBtn).toBeEnabled()
    await nextBtn.click()

    // ── Step 2: App Name ─────────────────────────────────────────────────────
    await expect(page.getByText('Set App Name')).toBeVisible()

    // The app name input has placeholder "Jongji" and a default value
    const appNameInput = page.getByPlaceholder('Jongji')
    await expect(appNameInput).toBeVisible()

    // Clear and type our E2E app name
    await appNameInput.fill(TEST_APP_NAME)

    await page.getByRole('button', { name: 'Next' }).click()

    // ── Step 3: Google OAuth (Optional) ─────────────────────────────────────
    await expect(page.getByText('Google OAuth (Optional)')).toBeVisible()
    await page.getByRole('button', { name: 'Skip' }).click()

    // ── Step 4: Confirm ──────────────────────────────────────────────────────
    await expect(page.getByText('Confirm Setup')).toBeVisible()

    // Review shows the admin email and app name
    await expect(page.getByText(TEST_ADMIN.email)).toBeVisible()
    await expect(page.getByText(TEST_APP_NAME)).toBeVisible()

    // Submit
    const submitBtn = page.getByRole('button', { name: 'Complete Setup' })
    await expect(submitBtn).toBeEnabled()
    await submitBtn.click()

    // ── Redirect ─────────────────────────────────────────────────────────────
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
  })

  test('Next button is disabled when Step 1 fields are empty', async ({ page }) => {
    await page.goto('/setup')

    await expect(page.getByText('Create Admin Account')).toBeVisible()

    const nextBtn = page.getByRole('button', { name: 'Next' })
    await expect(nextBtn).toBeDisabled()
  })

  test('Next button enables only when all required Step 1 fields are filled', async ({ page }) => {
    await page.goto('/setup')

    const nextBtn = page.getByRole('button', { name: 'Next' })

    // Only name filled — still disabled
    await page.getByPlaceholder('Jane Doe').fill('Admin')
    await expect(nextBtn).toBeDisabled()

    // Name + email — still disabled
    await page.getByPlaceholder('admin@example.com').fill('admin@test.com')
    await expect(nextBtn).toBeDisabled()

    // All three filled with sufficient password length
    await page.getByPlaceholder('••••••••').fill('TestPass1!')
    await expect(nextBtn).toBeEnabled()
  })

  test('can navigate Back from Step 2 to Step 1', async ({ page }) => {
    await page.goto('/setup')

    await page.getByPlaceholder('Jane Doe').fill(TEST_ADMIN.name)
    await page.getByPlaceholder('admin@example.com').fill(TEST_ADMIN.email)
    await page.getByPlaceholder('••••••••').fill(TEST_ADMIN.password)
    await page.getByRole('button', { name: 'Next' }).click()

    await expect(page.getByText('Set App Name')).toBeVisible()

    await page.getByRole('button', { name: 'Back' }).click()

    await expect(page.getByText('Create Admin Account')).toBeVisible()
  })
})
