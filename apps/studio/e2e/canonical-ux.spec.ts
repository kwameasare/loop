import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 720 },
  { name: "mobile", width: 390, height: 844 },
] as const;

async function seedLoopSession(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem(
      "loop.cp.session",
      JSON.stringify({
        access_token: "loop-session-canonical-ux",
        session_token: "loop-session-canonical-ux",
        refresh_token: "refresh-canonical-ux",
        token_type: "Bearer",
        expires_in: 1800,
        stored_at: Date.now(),
      }),
    );
  });
}

async function openAgents(page: Page) {
  await seedLoopSession(page);
  await page.goto("/agents");
  await expect(page).toHaveURL(/\/agents$/);
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
}

async function openAgentWorkbench(page: Page) {
  await seedLoopSession(page);
  await page.goto("/agents/agent-enterprise-support");
  await expect(page.getByTestId("agent-detail-shell")).toBeVisible();
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

for (const viewport of VIEWPORTS) {
  test(`canonical shell smoke covers contextual layout and keyboard on ${viewport.name}`, async ({
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
    await expect(page.getByTestId("live-preview-rail")).toHaveCount(0);
    await expect(page.getByTestId("activity-timeline")).toHaveCount(0);
    await expect(page.getByTestId("status-footer")).toHaveCount(0);

    for (const section of [
      "build",
      "test",
      "ship",
      "observe",
      "migrate",
      "govern",
    ]) {
      await expect(page.getByTestId(`nav-section-${section}`)).toBeVisible();
    }

    await expect(page.getByTestId("nav-agents")).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(page.getByTestId("agents-empty")).toContainText(
      "No agents yet",
    );
    await expect(page.getByText("Canary 12%")).toHaveCount(0);
    await expect(page.getByText("trace_refund_742")).toHaveCount(0);

    await expectNoHorizontalOverflow(page);

    await page.keyboard.press("Tab");
    await expectVisibleFocus(page);

    await page.keyboard.press("Control+K");
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await expect(page.getByTestId("command-input")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toBeHidden();
  });
}

test("agent workbench keeps sections local and avoids fixture evidence", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openAgentWorkbench(page);

  await expect(page.getByTestId("agent-local-nav")).toBeVisible();
  await expect(page.getByTestId("agent-local-topbar")).toContainText(
    "Production is not live",
  );
  await expect(page.getByTestId("agent-tab-contract")).toBeVisible();
  await expect(page.getByTestId("agent-tab-evals")).toBeVisible();
  await expect(page.getByTestId("agent-tab-traces")).toBeVisible();
  await expect(page.getByTestId("agent-tab-governance")).toBeVisible();
  await expect(page.getByTestId("agent-state-sentence")).toContainText(
    "create a commitment",
  );
  await expect(page.getByTestId("agent-outline-commitment")).toContainText(
    "draft v0",
  );
  await expect(page.getByText("trace_refund_742")).toHaveCount(0);
  await expect(
    page.getByText("I need to cancel my annual renewal"),
  ).toHaveCount(0);

  await page.getByTestId("agent-tab-contract").click();
  await expect(page).toHaveURL(/\/agents\/agent-enterprise-support\/contract$/);
  await expect(page.getByTestId("agent-contract-panel")).toContainText(
    "Commitment Document",
  );
  await expect(page.getByTestId("contract-missing-fields")).toContainText(
    "Business responsibility",
  );

  await page.getByTestId("agent-tab-channels").click();
  await expect(page).toHaveURL(/\/agents\/agent-enterprise-support\/channels$/);
  await expect(page.getByTestId("channel-bindings-panel")).toContainText(
    "Voice is a channel binding",
  );
  await expect(page.getByTestId("channel-binding-whatsapp")).toBeVisible();
  await expect(page.getByTestId("channel-binding-telegram")).toBeVisible();
  await expect(page.getByTestId("channel-binding-voice")).toBeVisible();

  await page.getByTestId("agent-tab-deploys").click();
  await expect(page).toHaveURL(/\/agents\/agent-enterprise-support\/deploys$/);
  await expect(page.getByTestId("change-package-panel")).toContainText(
    "Change Package",
  );
  await expect(page.getByTestId("change-package-status")).toContainText(
    "draft",
  );
  await expect(page.getByText("trace_refund_742")).toHaveCount(0);
});
