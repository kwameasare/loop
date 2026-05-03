/**
 * S912: Playwright config for the studio Auth0 happy-path e2e.
 *
 * The test stubs Auth0 (universal login + /oauth/token) and cp-api
 * (`/v1/auth/exchange`) via ``page.route`` so the spec runs against a
 * locally-served ``next dev`` without a live tenant. CI picks the
 * spec up via ``pnpm test:e2e``; ``LOOP_E2E_BASE_URL`` overrides the
 * studio base URL for staging smokes.
 */
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.LOOP_E2E_BASE_URL || "http://127.0.0.1:3001";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: process.env.LOOP_E2E_BASE_URL
    ? undefined
    : {
        command:
          "LOOP_AUTH0_DOMAIN=auth0.test LOOP_AUTH0_CLIENT_ID=client-test NEXT_PUBLIC_LOOP_API_URL=http://127.0.0.1:3001/__cp pnpm dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
