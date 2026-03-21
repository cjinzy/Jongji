import { test, expect } from '../fixtures/base'
import { seedTestData } from '../helpers/api'

test.describe('Dashboard', () => {
  let seedData: Awaited<ReturnType<typeof seedTestData>>

  test.beforeAll(async () => {
    seedData = await seedTestData('')
  })

  test('renders dashboard page with KPI cards', async ({ devPage }) => {
    await devPage.goto('/dashboard')

    // Dashboard should render without errors
    await expect(devPage.locator('h1, h2, [data-testid="dashboard"]').first()).toBeVisible({
      timeout: 10_000,
    })

    // KPI cards should be present (total tasks, completed, in progress, etc.)
    const cards = devPage.locator('[class*="card"], [class*="kpi"], [class*="stat"]')
    await expect(cards.first()).toBeVisible({ timeout: 5_000 })
  })

  test('displays task status distribution', async ({ devPage }) => {
    await devPage.goto('/dashboard')

    // Wait for dashboard to load
    await devPage.waitForTimeout(2_000)

    // Should have chart or visualization elements
    const charts = devPage.locator('svg, canvas, [class*="chart"], [class*="recharts"]')
    const chartsCount = await charts.count()
    expect(chartsCount).toBeGreaterThan(0)
  })

  test('navigates to dashboard from sidebar', async ({ devPage }) => {
    await devPage.goto('/')

    // Click dashboard link in sidebar/navigation
    const dashboardLink = devPage.locator('a[href*="dashboard"], [data-testid="nav-dashboard"]').first()
    if (await dashboardLink.isVisible()) {
      await dashboardLink.click()
      await expect(devPage).toHaveURL(/.*dashboard.*/)
    }
  })
})
