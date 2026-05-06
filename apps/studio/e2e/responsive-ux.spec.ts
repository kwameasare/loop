import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844, mode: "mobile" },
  { name: "tablet", width: 900, height: 1280, mode: "tablet" },
  { name: "desktop", width: 1440, height: 900, mode: "desktop" },
  { name: "large-display", width: 2400, height: 1400, mode: "large-display" },
] as const;

for (const vp of VIEWPORTS) {
  test(`responsive demo route resolves to ${vp.mode} for ${vp.width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/responsive");
    const surface = page.getByTestId(`responsive-surface-${vp.mode}`);
    await expect(surface).toBeVisible();
    // Second-monitor strip is persistent across every mode.
    await expect(page.getByTestId("second-monitor")).toBeVisible();
    await expect(page.getByTestId("second-monitor-timeline")).toBeVisible();
    await expect(page.getByTestId("second-monitor-production-tail")).toBeVisible();
    await expect(page.getByTestId("second-monitor-inbox")).toBeVisible();
    await expect(page.getByTestId("second-monitor-deploy-health")).toBeVisible();
  });
}

test("mobile mode never exposes full-edit affordances", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/responsive");
  await expect(page.getByTestId("mobile-action-deck")).toBeVisible();
  // The mobile action deck only contains the eight urgent buttons.
  const buttons = page.getByTestId("mobile-action-list").getByRole("button");
  await expect(buttons).toHaveCount(8);
  // No agent editor anywhere on the page.
  await expect(page.getByText(/edit agent/i)).toHaveCount(0);
});

test("forcing tablet via switcher shows review surfaces", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/responsive");
  await page.getByTestId("responsive-mode-tablet").click();
  await expect(page.getByTestId("tablet-review-pane")).toBeVisible();
  await expect(page.getByTestId("tablet-surface-approvals")).toBeVisible();
  await expect(page.getByTestId("tablet-surface-parity-report")).toBeVisible();
});
