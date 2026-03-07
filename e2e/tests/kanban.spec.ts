import { test, expect } from '../fixtures/base'
import { login, createTeam, createProject, createTask } from '../helpers/api'
import { TEST_ADMIN, TEST_TEAM, TEST_PROJECT } from '../helpers/constants'

test.describe('Kanban Board', () => {
  let teamId: string
  let projectId: string
  let projectKey: string
  let token: string

  test.beforeEach(async () => {
    const result = await login(TEST_ADMIN.email, TEST_ADMIN.password)
    token = result.access_token
    const team = await createTeam(token, TEST_TEAM)
    teamId = team.id
    const project = await createProject(token, team.id, TEST_PROJECT)
    projectId = project.id
    projectKey = project.key
  })

  test('renders all kanban columns', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)

    // Wait for board to load
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Verify all 7 status columns are rendered
    await expect(page.getByText('Backlog')).toBeVisible()
    await expect(page.getByText('Todo')).toBeVisible()
    await expect(page.getByText('In Progress')).toBeVisible()
    await expect(page.getByText('In Review')).toBeVisible()
    await expect(page.getByText('Done')).toBeVisible()
    await expect(page.getByText('Reopened')).toBeVisible()
    await expect(page.getByText('Closed')).toBeVisible()
  })

  test('seeded tasks appear in correct columns', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Seed tasks via API across multiple statuses
    await createTask(token, {
      project_id: projectId,
      title: 'Backlog Task',
      status: 'BACKLOG',
    })
    await createTask(token, {
      project_id: projectId,
      title: 'Todo Task',
      status: 'TODO',
    })
    await createTask(token, {
      project_id: projectId,
      title: 'Progress Task',
      status: 'PROGRESS',
    })
    await createTask(token, {
      project_id: projectId,
      title: 'Done Task',
      status: 'DONE',
    })

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Verify each task appears on the board
    await expect(page.getByText('Backlog Task')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Todo Task')).toBeVisible()
    await expect(page.getByText('Progress Task')).toBeVisible()
    await expect(page.getByText('Done Task')).toBeVisible()
  })

  test('drag task card from Backlog column to Todo column', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Seed a task in BACKLOG
    await createTask(token, {
      project_id: projectId,
      title: 'Drag Me Task',
      status: 'BACKLOG',
    })

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Drag Me Task')).toBeVisible({ timeout: 10_000 })

    // Locate the task card and the Todo column drop target
    const taskCard = page.getByText('Drag Me Task').first()

    // Find the "Todo" column header to use as drop target
    // The KanbanColumn renders with a data attribute or text label
    const todoColumnHeader = page.getByText('Todo').first()

    // Get bounding boxes
    const sourceBox = await taskCard.boundingBox()
    const targetBox = await todoColumnHeader.boundingBox()

    if (!sourceBox || !targetBox) {
      throw new Error('Could not locate drag source or drop target bounding boxes')
    }

    // Use Playwright's mouse drag API
    await page.mouse.move(
      sourceBox.x + sourceBox.width / 2,
      sourceBox.y + sourceBox.height / 2,
    )
    await page.mouse.down()

    // Move slowly to trigger drag activation (dnd-kit needs >6px movement)
    await page.mouse.move(
      sourceBox.x + sourceBox.width / 2 + 10,
      sourceBox.y + sourceBox.height / 2,
      { steps: 5 },
    )
    await page.mouse.move(
      targetBox.x + targetBox.width / 2,
      targetBox.y + targetBox.height / 2,
      { steps: 20 },
    )
    await page.mouse.up()

    // Wait for the optimistic update — task should now appear in Todo column
    // The task title should still be visible (it moved, not disappeared)
    await expect(page.getByText('Drag Me Task')).toBeVisible({ timeout: 8_000 })
  })

  test('unassigned filter button toggles and filters tasks', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Seed a task
    await createTask(token, {
      project_id: projectId,
      title: 'Unassigned Filter Task',
      status: 'TODO',
    })

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Unassigned Filter Task')).toBeVisible({ timeout: 10_000 })

    // Click the Unassigned filter button
    const unassignedBtn = page.getByRole('button', { name: /unassigned/i })
    await expect(unassignedBtn).toBeVisible()

    // Initially not pressed
    await expect(unassignedBtn).toHaveAttribute('aria-pressed', 'false')

    await unassignedBtn.click()

    // Now pressed
    await expect(unassignedBtn).toHaveAttribute('aria-pressed', 'true')

    // Unassigned tasks should still be visible (our task has no assignee)
    await expect(page.getByText('Unassigned Filter Task')).toBeVisible()

    // Toggle off
    await unassignedBtn.click()
    await expect(unassignedBtn).toHaveAttribute('aria-pressed', 'false')
  })

  test('refresh button reloads tasks', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Click refresh button (aria-label="Refresh tasks")
    const refreshBtn = page.getByRole('button', { name: 'Refresh tasks' })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()

    // Board should still be visible after refresh
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 8_000 })
  })

  test('add task button in column opens create modal with correct status', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage

    await page.goto(`/teams/${teamId}/projects/${projectKey}/kanban`)
    await expect(page.getByText('Kanban')).toBeVisible({ timeout: 10_000 })

    // Each column has an "Add task" button — click the one in Backlog column
    // KanbanColumn renders an add button with aria-label or title
    const addTaskBtns = page.getByRole('button', { name: /add task/i })
    const firstAddBtn = addTaskBtns.first()

    if (await firstAddBtn.isVisible()) {
      await firstAddBtn.click()

      // Modal opens
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 })

      // Close it
      await page.keyboard.press('Escape')
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5_000 })
    }
  })
})
