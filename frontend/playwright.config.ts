import { defineConfig } from '@playwright/test'

const baseURL = 'http://127.0.0.1:8769'

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  timeout: 45_000,
  workers: 1,
  use: { baseURL, trace: 'retain-on-failure' },
  webServer: {
    command: 'python -m tests.browser_app',
    cwd: '..',
    url: baseURL,
    reuseExistingServer: false,
  },
})
