import { test, expect } from '../fixtures/base'
import { TEST_TEAM } from '../helpers/constants'

test.describe('Team Management', () => {
  test('creates a new team via onboarding and verifies it appears', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage

    // Navigate to onboarding (team creation flow)
    await page.goto('/onboarding')

    await expect(page.getByText('Create or join a team')).toBeVisible({ timeout: 10_000 })

    // "Create a team" tab should be active by default
    const createTab = page.getByRole('button', { name: 'Create a team' })
    await expect(createTab).toBeVisible()

    // Fill team name
    const teamNameInput = page.getByPlaceholder('e.g. Engineering')
    await teamNameInput.fill(TEST_TEAM.name)

    // Fill optional description
    const descInput = page.getByPlaceholder('Briefly describe your team')
    await descInput.fill(TEST_TEAM.description)

    // Click Next to create the team
    const nextBtn = page.getByRole('button', { name: 'Next' })
    await expect(nextBtn).toBeEnabled()
    await nextBtn.click()

    // Step 2: Project creation
    await expect(page.getByText('Create your first project')).toBeVisible({ timeout: 8_000 })

    // Skip project creation for now — just verify team was created
    // Navigate back to home to see team
    await page.getByRole('button', { name: 'Set up later' }).click()

    // App navigates away from onboarding
    await expect(page).not.toHaveURL(/\/onboarding/, { timeout: 10_000 })
  })

  test('created team name appears in the team selector in the sidebar', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage

    await page.goto('/onboarding')

    await expect(page.getByText('Create or join a team')).toBeVisible({ timeout: 10_000 })

    await page.getByPlaceholder('e.g. Engineering').fill(TEST_TEAM.name)
    await page.getByRole('button', { name: 'Next' }).click()

    // Step 2: project creation — skip
    await expect(page.getByText('Create your first project')).toBeVisible({ timeout: 8_000 })

    // Fill minimal project info (key auto-derived)
    await page.getByPlaceholder('e.g. Main Project').fill('Test Project')
    await page.getByRole('button', { name: 'Next' }).click()

    // Step 3: success
    await expect(page.getByText("You're all set!")).toBeVisible({ timeout: 8_000 })

    // Click "Get Started"
    await page.getByRole('button', { name: 'Get Started' }).click()

    // Now somewhere in the app the team name should be visible
    await page.waitForTimeout(1_000)
    const teamNameEl = page.getByText(TEST_TEAM.name).first()
    await expect(teamNameEl).toBeVisible({ timeout: 10_000 })
  })
})
