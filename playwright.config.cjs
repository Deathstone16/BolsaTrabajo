const { defineConfig, devices } = require('@playwright/test');
const path = require('node:path');

const artifacts = process.env.E2E_RUN_DIR || path.join(__dirname, '.test-artifacts', 'e2e', 'manual');
module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  outputDir: path.join(artifacts, 'results'),
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(artifacts, 'html'), open: 'never' }],
    ['json', { outputFile: path.join(artifacts, 'results.json') }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000',
    ...devices['Desktop Chrome'],
    locale: 'es-AR',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium' }],
});
