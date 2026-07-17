import { defineConfig, devices } from '@playwright/test'

/**
 * E2E smoke suite. Boots both servers itself:
 *  - FastAPI on :8000 in OFFLINE mode (DELTA_NO_ENV_FILE / DELTA_OFFLINE) so
 *    every LLM feature serves its deterministic seed-data fallback — tests
 *    never flake on generated text and never bill the API key.
 *  - Vite dev server on :5173 (no service worker in dev, so the PWA cache
 *    can never serve a stale build to the tests).
 * If a server is already running on either port it is reused — make sure a
 * reused backend was started offline, or scenario tests may hit the live API.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  // serial: parallel workers pile onto the LLM-backed endpoints (scenarios,
  // agent-report) and time each other out when a real API key is configured
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list']],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://localhost:5173',
    locale: 'ar',
    trace: 'retain-on-failure',
    reducedMotion: 'reduce',
  },
  webServer: [
    {
      command: '.venv\\Scripts\\python -m uvicorn app.main:app --port 8000',
      cwd: '../backend',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      env: { DELTA_NO_ENV_FILE: '1', DELTA_OFFLINE: '1' },
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
