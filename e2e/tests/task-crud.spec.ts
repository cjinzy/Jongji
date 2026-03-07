import { test, expect } from '../fixtures/base'
import { login, createTeam, createProject } from '../helpers/api'
import { TEST_ADMIN, TEST_TEAM, TEST_PROJECT } from '../helpers/constants'

test.describe('Task CRUD', () => {
  let teamId: string
  let projectKey: string

  test.beforeEach(async () => {
    const { access_token } = await login(TEST_ADMIN.email, TEST_ADMIN.password)
    const team = await createTeam(access_token, TEST_TEAM)
    teamId = team.id
    const project = await createProject(access_token, team.id, TEST_PROJECT)
    projectKey = project.key
  })

  test('creates a task via Kanban board UI', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Navigate to the kanban board for our project
    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)

    // Wait for kanban board to load
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Click the "Create Task" button in the toolbar
    const createTaskBtn = page.getByRole('button', { name: 'Create Task' })
    await expect(createTaskBtn).toBeVisible()
    await createTaskBtn.click()

    // Task create modal should open
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 })

    // Fill in the task title
    const titleInput = page.getByPlaceholder('Task title...')
    await expect(titleInput).toBeVisible()
    await titleInput.fill('My E2E Test Task')

    // Fill in description
    const descInput = page.getByPlaceholder('Optional description...')
    await descInput.fill('This task was created by Playwright E2E test.')

    // Submit the form
    const submitBtn = page.getByRole('button', { name: 'Create Task' }).last()
    await submitBtn.click()

    // Modal should close
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 8_000 })

    // Task card should appear on the board
    await expect(page.getByText('My E2E Test Task')).toBeVisible({ timeout: 10_000 })
  })

  test('clicking a task card opens the detail panel', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Create a task first
    await page.getByRole('button', { name: 'Create Task' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 })
    await page.getByPlaceholder('Task title...').fill('Clickable Task')
    await page.getByRole('button', { name: 'Create Task' }).last().click()
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 8_000 })

    // The task card should be visible
    const taskCard = page.getByText('Clickable Task').first()
    await expect(taskCard).toBeVisible({ timeout: 10_000 })

    // Click it
    await taskCard.click()

    // Detail panel should open — it shows the task title
    await expect(page.getByText('Clickable Task').nth(1)).toBeVisible({ timeout: 8_000 })
  })

  test('task create modal closes on Cancel', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: 'Create Task' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 })

    // Click cancel
    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5_000 })
  })

  test('task create modal closes on Escape key', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: 'Create Task' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 })

    // Press Escape
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5_000 })
  })
})
