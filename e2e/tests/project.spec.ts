import { test, expect } from '../fixtures/base'
import { createTeam } from '../helpers/api'
import { TEST_ADMIN, TEST_TEAM, TEST_PROJECT } from '../helpers/constants'
import { login } from '../helpers/api'

test.describe('Project Management', () => {
  test('creates a project via team page UI and verifies it appears in project list', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage

    // Create team via API first
    const { access_token } = await login(TEST_ADMIN.email, TEST_ADMIN.password)
    const team = await createTeam(access_token, TEST_TEAM)

    // Navigate to team page
    await page.goto(`/teams/${team.id}`)

    await expect(page.getByText(TEST_TEAM.name)).toBeVisible({ timeout: 10_000 })

    // Click "New project" button
    const newProjectBtn = page.getByRole('button', { name: 'New project' })
    await expect(newProjectBtn).toBeVisible()
    await newProjectBtn.click()

    // Should navigate to new project creation page
    await expect(page).toHaveURL(/\/new-project/, { timeout: 8_000 })

    // Fill in project details — look for the onboarding step-2 style form
    await expect(page.getByText('Create your first project')).toBeVisible({ timeout: 8_000 })

    await page.getByPlaceholder('e.g. Main Project').fill(TEST_PROJECT.name)

    // Key gets auto-derived; override it
    const keyInput = page.getByPlaceholder('MAIN')
    await keyInput.fill(TEST_PROJECT.key)

    // Click Next
    await page.getByRole('button', { name: 'Next' }).click()

    // Step 3 success or redirect back to team
    // After creating project, navigate back to team page
    await page.waitForTimeout(1_000)

    // If we're on step 3, click Get Started
    const getStartedBtn = page.getByRole('button', { name: 'Get Started' })
    if (await getStartedBtn.isVisible()) {
      await getStartedBtn.click()
    }

    // Navigate to team page to verify project appears
    await page.goto(`/teams/${team.id}`)
    await expect(page.getByText(TEST_PROJECT.name)).toBeVisible({ timeout: 10_000 })
  })

  test('project Kanban link navigates to kanban board', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Use API to set up team + project
    const { access_token } = await login(TEST_ADMIN.email, TEST_ADMIN.password)
    const team = await createTeam(access_token, TEST_TEAM)

    // Create project via onboarding flow
    await page.goto('/onboarding')
    await page.getByPlaceholder('e.g. Engineering').fill(TEST_TEAM.name)

    // Navigate the onboarding: Step 1 Next creates team, but we already have one
    // Use the skip approach and navigate directly
    await page.getByRole('button', { name: 'Set up later' }).click()

    // Navigate to the team page directly
    await page.goto(`/teams/${team.id}`)
    await expect(page.getByText(TEST_TEAM.name)).toBeVisible({ timeout: 10_000 })

    // Click "New project" and create via UI
    const newProjectBtn = page.getByRole('button', { name: 'New project' })
    await newProjectBtn.click()

    await expect(page.getByText('Create your first project')).toBeVisible({ timeout: 8_000 })
    await page.getByPlaceholder('e.g. Main Project').fill(TEST_PROJECT.name)
    const keyInput = page.getByPlaceholder('MAIN')
    await keyInput.fill(TEST_PROJECT.key)
    await page.getByRole('button', { name: 'Next' }).click()

    // Skip or complete
    const getStartedBtn = page.getByRole('button', { name: 'Get Started' })
    if (await getStartedBtn.isVisible()) {
      await getStartedBtn.click()
    }

    await page.goto(`/teams/${team.id}`)
    await expect(page.getByText(TEST_PROJECT.name)).toBeVisible({ timeout: 10_000 })

    // Click Kanban link for the project
    const kanbanLink = page.getByTitle('Kanban').first()
    await kanbanLink.click()

    // Should navigate to kanban view
    await expect(page).toHaveURL(/\/kanban/, { timeout: 10_000 })
    await expect(page.getByText('Kanban')).toBeVisible()
  })
})
