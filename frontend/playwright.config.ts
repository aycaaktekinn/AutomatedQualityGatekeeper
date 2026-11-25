import { defineConfig, devices } from '@playwright/test'

// E2E tests run against the full stack (FastAPI serving the built UI).
// Start it with `uvicorn app.main:app --port 8000` from ../backend, or set E2E_BASE_URL.
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 90_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
