import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const SAMPLE_REPO = process.env.E2E_SAMPLE_REPO ?? 'https://github.com/pallets/itsdangerous'

test.describe('UC-02 Submit repository for analysis', () => {
  test('rejects a non-GitHub URL before calling the API (NFR-14)', async ({ page }) => {
    let apiCalled = false
    page.on('request', (req) => {
      if (req.url().includes('/api/analyses') && req.method() === 'POST') apiCalled = true
    })
    await page.goto('/')
    await page.getByTestId('repo-url').fill('https://gitlab.com/group/project')
    await page.getByTestId('analyse').click()
    await expect(page.getByTestId('error')).toContainText('https://github.com/<owner>/<repo>')
    expect(apiCalled).toBe(false)
  })

  test('shows the server message when the backend rejects the URL (FR-03)', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('repo-url').fill('https://github.com/example/..')
    await page.getByTestId('analyse').click()
    await expect(page.getByTestId('error')).toContainText('not valid')
  })
})

test.describe('UC-03 / UC-04 View score and inspect issues', () => {
  test('analyses a real repository end to end', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('repo-url').fill(SAMPLE_REPO)
    await page.getByTestId('analyse').click()

    await expect(page).toHaveURL(/#\/analyses\/[0-9a-f-]{36}$/)
    await expect(page.getByTestId('status')).toHaveText(/Completed|Partial result/)
    await expect(page.getByTestId('grade').first()).toHaveText(/^[A-E]$/)

    for (const characteristic of ['maintainability', 'security', 'reliability']) {
      await expect(page.getByTestId(`score-${characteristic}`)).toBeVisible()
    }
    await expect(page.getByTestId('tools')).toContainText('radon')

    // FR-08: filtering by characteristic only shows that characteristic.
    await page.getByTestId('filter-characteristic').selectOption('security')
    const rows = page.locator('[data-testid="findings"] .finding-row')
    await expect(rows.first()).toBeVisible()
    // Wait for the filtered list (the UI debounces filter changes) instead of reading it once.
    await expect(rows.locator('td:nth-child(2)').filter({ hasNotText: 'security' })).toHaveCount(0)

    // FR-09: a finding opens its code snippet as plain text.
    await rows.first().click()
    await expect(page.locator('.snippet-row pre')).toBeVisible()
  })
})

test('home page has no serious accessibility violations (NFR-13)', async ({ page }) => {
  await page.goto('/')
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  const serious = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact ?? ''))
  expect(serious.map((v) => v.id)).toEqual([])
})

test.describe('FR-14 Stop a running analysis', () => {
  const LARGE_REPO = process.env.E2E_LARGE_REPO ?? 'https://github.com/python/mypy'

  test('shows progress and stops when the user presses Stop', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('repo-url').fill(LARGE_REPO)
    await page.getByTestId('analyse').click()

    await expect(page.getByTestId('stage')).toBeVisible()
    await expect(page.getByTestId('stage')).toContainText(/Cloning|Running|Reading|Checking|Waiting/)
    await page.getByTestId('stop').click()

    await expect(page.getByTestId('status')).toHaveText('Cancelled', { timeout: 10_000 })
    await expect(page.getByTestId('cancelled')).toBeVisible()
    await expect(page.getByTestId('stop')).toHaveCount(0)
  })
})
