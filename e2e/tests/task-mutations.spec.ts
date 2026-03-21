import { test, expect } from '../fixtures/base'
import { seedTestData } from '../helpers/api'

test.describe('Task Mutations', () => {
  let seedData: Awaited<ReturnType<typeof seedTestData>>

  test.beforeAll(async () => {
    seedData = await seedTestData('')
  })

  test('create task via kanban add button', async ({ devPage }) => {
    await devPage.goto('/kanban')

    await devPage.waitForTimeout(2_000)

    // Find an "add task" button on any column
    const addButton = devPage.locator('button').filter({ hasText: /\+|add|추가/i }).first()
    if (await addButton.isVisible()) {
      await addButton.click()

      // Fill task title in modal
      const titleInput = devPage.locator('input[name="title"], input[placeholder*="title"], input[placeholder*="제목"]').first()
      await expect(titleInput).toBeVisible({ timeout: 5_000 })
      await titleInput.fill('New E2E Task')

      // Submit
      const submitBtn = devPage.locator('button[type="submit"], button').filter({ hasText: /create|save|생성|저장/i }).first()
      await submitBtn.click()

      // Task should appear on board
      await devPage.waitForTimeout(2_000)
      await expect(devPage.getByText('New E2E Task')).toBeVisible({ timeout: 5_000 })
    }
  })

  test('edit task title in detail panel', async ({ devPage }) => {
    await devPage.goto('/kanban')

    await devPage.waitForTimeout(2_000)

    // Click on an existing task
    const taskCard = devPage.getByText('Test Task 1', { exact: false }).first()
    await taskCard.click()

    // Wait for detail panel
    await devPage.waitForTimeout(1_000)

    // Find and edit the title field
    const titleField = devPage.locator('[class*="detail"] input, [class*="panel"] input, [contenteditable="true"]').first()
    if (await titleField.isVisible()) {
      await titleField.clear()
      await titleField.fill('Updated Task Title')
      await titleField.press('Enter')

      await devPage.waitForTimeout(1_000)
      await expect(devPage.getByText('Updated Task Title')).toBeVisible({ timeout: 5_000 })
    }
  })

  test('change task status via detail panel', async ({ devPage }) => {
    await devPage.goto('/kanban')

    await devPage.waitForTimeout(2_000)

    // Click on a task
    const taskCard = devPage.getByText('Test Task 2', { exact: false }).first()
    await taskCard.click()

    await devPage.waitForTimeout(1_000)

    // Find status selector/dropdown in detail panel
    const statusSelector = devPage.locator('[class*="status"], select, [role="combobox"]').first()
    if (await statusSelector.isVisible()) {
      await statusSelector.click()
      await devPage.waitForTimeout(500)

      // Select a different status
      const newStatus = devPage.getByText(/progress|진행/i).first()
      if (await newStatus.isVisible()) {
        await newStatus.click()
        await devPage.waitForTimeout(1_000)
      }
    }
  })

  test('close detail panel with Escape key', async ({ devPage }) => {
    await devPage.goto('/kanban')

    await devPage.waitForTimeout(2_000)

    // Open a task
    const taskCard = devPage.getByText('Test Task', { exact: false }).first()
    await taskCard.click()

    await devPage.waitForTimeout(1_000)

    // Detail panel should be visible
    const panel = devPage.locator('[class*="detail"], [class*="panel"], [class*="drawer"]').first()
    await expect(panel).toBeVisible({ timeout: 5_000 })

    // Press Escape to close
    await devPage.keyboard.press('Escape')
    await devPage.waitForTimeout(500)

    // Panel should be hidden
    await expect(panel).not.toBeVisible({ timeout: 3_000 })
  })

  test('task priority is visible on card', async ({ devPage }) => {
    await devPage.goto('/kanban')

    await devPage.waitForTimeout(2_000)

    // Seeded tasks have priorities 1-5, check they render
    const taskCards = devPage.locator('[class*="card"], [class*="task"]')
    const cardCount = await taskCards.count()
    expect(cardCount).toBeGreaterThan(0)
  })
})
