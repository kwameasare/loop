import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 720 },
  { name: "mobile", width: 390, height: 844 },
] as const;

async function mockLocalLogin(page: Page) {
  await page.route("**/api/dev-login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "loop-session-canonical-ux",
        session_token: "loop-session-canonical-ux",
        refresh_token: "refresh-canonical-ux",
        token_type: "Bearer",
        expires_in: 1800,
      }),
    });
  });
}

async function openAgents(page: Page) {
  await mockLocalLogin(page);
  await page.goto("/agents");
  await expect(
    page.getByRole("heading", { name: "Sign in (local pilot)" }),
  ).toBeVisible();
  await page.getByTestId("dev-login-submit").click();
  await expect(page).toHaveURL(/\/agents$/);
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() =>
    Math.max(
      document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
      document.body.scrollWidth - window.innerWidth,
    ),
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

async function expectVisibleFocus(page: Page) {
  const focusStyle = await page.evaluate(() => {
    const element = document.activeElement;
    if (!element || element === document.body) return null;
    const style = window.getComputedStyle(element);
    return {
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      boxShadow: style.boxShadow,
    };
  });

  expect(focusStyle).not.toBeNull();
  expect(
    focusStyle!.outlineStyle !== "none" ||
      focusStyle!.outlineWidth !== "0px" ||
      focusStyle!.boxShadow !== "none",
  ).toBeTruthy();
}

async function expectReducedMotionHonored(page: Page) {
  const canarySignal = page
    .getByTestId("live-preview-rail")
    .getByTestId("live-badge")
    .filter({ hasText: "Canary 12%" })
    .locator("[aria-hidden='true']");
  await expect(canarySignal).toBeVisible();

  const motion = await canarySignal.evaluate((element) => {
    const style = window.getComputedStyle(element);
    const seconds = style.animationDuration
      .split(",")
      .map((value) => value.trim())
      .map((value) =>
        value.endsWith("ms")
          ? Number.parseFloat(value) / 1000
          : Number.parseFloat(value),
      );
    return {
      maxDuration: Math.max(...seconds.filter(Number.isFinite)),
      iterationCount: style.animationIterationCount,
    };
  });

  expect(motion.maxDuration).toBeLessThanOrEqual(0.001);
  expect(motion.iterationCount).toBe("1");
}

for (const viewport of VIEWPORTS) {
  test(`canonical shell smoke covers layout, keyboard, status, and motion on ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openAgents(page);

    await expect(page.getByTestId("app-shell")).toBeVisible();
    await expect(page.getByTestId("asset-rail")).toBeVisible();
    await expect(page.getByTestId("topbar")).toBeVisible();
    await expect(page.getByTestId("work-surface")).toBeVisible();
    await expect(page.getByTestId("live-preview-rail")).toBeVisible();
    await expect(page.getByTestId("activity-timeline")).toBeVisible();
    await expect(page.getByTestId("status-footer")).toBeVisible();

    for (const section of [
      "Build",
      "Test",
      "Ship",
      "Observe",
      "Migrate",
      "Govern",
    ]) {
      await expect(
        page.getByRole("heading", { name: section, exact: true }),
      ).toBeVisible();
    }

    await expect(page.getByTestId("nav-agents")).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(page.getByTestId("agents-empty")).toContainText(
      "No agents yet",
    );
    await expect(page.getByText("Control plane healthy")).toBeVisible();
    await expect(page.getByText("Environment: dev")).toBeVisible();
    await expect(page.getByText("Canary 12%")).toBeVisible();

    await expectNoHorizontalOverflow(page);

    await page.keyboard.press("Tab");
    await expectVisibleFocus(page);

    await page.keyboard.press("Control+K");
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await expect(page.getByTestId("command-input")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toBeHidden();

    await expectReducedMotionHonored(page);
  });
}
