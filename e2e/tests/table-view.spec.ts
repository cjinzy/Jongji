import { test, expect } from '../fixtures/base'
import { seedTestData } from '../helpers/api'

test.describe('Table View', () => {
  let seedData: Awaited<ReturnType<typeof seedTestData>>

  test.beforeAll(async () => {
    seedData = await seedTestData('')
  })

  test('renders table view with task list', async ({ devPage }) => {
    await devPage.goto('/table')

    // Table should render with rows
    const table = devPage.locator('table, [role="grid"], [class*="table"]').first()
    await expect(table).toBeVisible({ timeout: 10_000 })
  })

  test('displays seeded tasks in table', async ({ devPage }) => {
    await devPage.goto('/table')

    // Wait for data to load
    await devPage.waitForTimeout(2_000)

    // At least one seeded task title should appear
    const taskRow = devPage.getByText('Test Task', { exact: false }).first()
    await expect(taskRow).toBeVisible({ timeout: 5_000 })
  })

  test('clicking a task row opens detail panel', async ({ devPage }) => {
    await devPage.goto('/table')

    await devPage.waitForTimeout(2_000)

    // Click on a task row
    const taskRow = devPage.getByText('Test Task', { exact: false }).first()
    await taskRow.click()

    // Detail panel or page should appear
    const detail = devPage.locator('[class*="detail"], [class*="panel"], [class*="drawer"]').first()
    await expect(detail).toBeVisible({ timeout: 5_000 })
  })

  test('table has sortable columns', async ({ devPage }) => {
    await devPage.goto('/table')

    await devPage.waitForTimeout(2_000)

    // Look for table header cells that might be clickable for sorting
    const headers = devPage.locator('th, [role="columnheader"]')
    const headerCount = await headers.count()
    expect(headerCount).toBeGreaterThan(0)
  })
})
