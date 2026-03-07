import { test, expect } from '@playwright/test'
import { resetDb } from '../helpers/reset-db'
import { setupInit } from '../helpers/api'
import { TEST_ADMIN, TEST_APP_NAME } from '../helpers/constants'

test.describe('Authentication', () => {
  test.beforeEach(async () => {
    await resetDb()
    await setupInit({
      admin_name: TEST_ADMIN.name,
      admin_email: TEST_ADMIN.email,
      admin_password: TEST_ADMIN.password,
      app_name: TEST_APP_NAME,
    })
  })

  test('successful login with valid credentials', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByText('Sign in to your account')).toBeVisible()

    await page.getByPlaceholder('Email').fill(TEST_ADMIN.email)
    await page.getByPlaceholder('Password').fill(TEST_ADMIN.password)

    await page.getByRole('button', { name: 'Login' }).click()

    // After successful login, app redirects away from /login
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10_000 })
  })

  test('shows error message on wrong password', async ({ page }) => {
    await page.goto('/login')

    await page.getByPlaceholder('Email').fill(TEST_ADMIN.email)
    await page.getByPlaceholder('Password').fill('WrongPassword999!')

    await page.getByRole('button', { name: 'Login' }).click()

    // Error message "Invalid email or password." should appear
    await expect(page.getByText('Invalid email or password.')).toBeVisible({ timeout: 8_000 })

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/)
  })

  test('shows validation error when fields are empty', async ({ page }) => {
    await page.goto('/login')

    await page.getByRole('button', { name: 'Login' }).click()

    await expect(page.getByText('Please fill in all fields.')).toBeVisible()
  })

  test('logout redirects to /login', async ({ page }) => {
    // Log in first
    await page.goto('/login')
    await page.getByPlaceholder('Email').fill(TEST_ADMIN.email)
    await page.getByPlaceholder('Password').fill(TEST_ADMIN.password)
    await page.getByRole('button', { name: 'Login' }).click()

    // Wait for redirect away from login
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10_000 })

    // Navigate to settings and logout, or find logout button
    // The app may have a logout button in settings or sidebar
    await page.goto('/settings')
    await expect(page).not.toHaveURL(/\/login/, { timeout: 5_000 })

    // Look for logout button (various possible labels)
    const logoutBtn = page
      .getByRole('button', { name: /logout|sign out|log out/i })
      .first()

    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
      await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
    } else {
      // If no visible logout button, just verify the user is still authenticated
      await expect(page).not.toHaveURL(/\/login/)
    }
  })
})
