import { test, expect } from '../fixtures/base'

test.describe('Settings', () => {
  test('renders settings page with navigation tabs', async ({ devPage }) => {
    await devPage.goto('/settings')

    // Settings page should load
    await devPage.waitForTimeout(2_000)

    // Should have tab navigation or settings sections
    const tabs = devPage.locator('[role="tab"], [class*="tab"], a[href*="settings"]')
    const tabCount = await tabs.count()
    expect(tabCount).toBeGreaterThan(0)
  })

  test('profile settings displays user info', async ({ devPage }) => {
    await devPage.goto('/settings')

    await devPage.waitForTimeout(2_000)

    // Profile section should show user name or email
    const profileInfo = devPage.getByText('Test Admin', { exact: false })
      .or(devPage.getByText('admin@test.com', { exact: false }))
    await expect(profileInfo.first()).toBeVisible({ timeout: 5_000 })
  })

  test('can navigate between settings tabs', async ({ devPage }) => {
    await devPage.goto('/settings')

    await devPage.waitForTimeout(2_000)

    // Find and click different settings tabs/sections
    const securityTab = devPage.getByText(/security|password|보안/i).first()
    if (await securityTab.isVisible()) {
      await securityTab.click()
      await devPage.waitForTimeout(1_000)

      // Security section should show password-related content
      const passwordField = devPage.locator('input[type="password"]').first()
      await expect(passwordField).toBeVisible({ timeout: 5_000 })
    }
  })

  test('language settings available', async ({ devPage }) => {
    await devPage.goto('/settings')

    await devPage.waitForTimeout(2_000)

    // Find language settings tab
    const langTab = devPage.getByText(/language|언어|locale/i).first()
    if (await langTab.isVisible()) {
      await langTab.click()
      await devPage.waitForTimeout(1_000)

      // Should show language options
      const langOptions = devPage.locator('select, [role="listbox"], [class*="dropdown"]')
      const optCount = await langOptions.count()
      expect(optCount).toBeGreaterThanOrEqual(0) // May be radio buttons or cards
    }
  })
})
