import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/visual',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: 'test-results',
  use: { baseURL: 'http://127.0.0.1:4175', browserName: 'chromium', channel: 'msedge',
    headless: true, viewport: { width: 1440, height: 1000 }, locale: 'tr-TR',
    timezoneId: 'Europe/Istanbul', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175', reuseExistingServer: true, timeout: 60000 },
});
