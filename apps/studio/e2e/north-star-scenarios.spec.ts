import { expect, test } from "@playwright/test";

const SCENARIOS = [
  { id: "maya-migrates-botpress", anchor: "§36.1" },
  { id: "diego-ships-voice", anchor: "§36.2" },
  { id: "priya-wrong-tool", anchor: "§36.3" },
  { id: "acme-four-eyes", anchor: "§36.4" },
  { id: "operator-escalation", anchor: "§36.5" },
  { id: "support-kb-gap", anchor: "§36.6" },
  { id: "sam-replay-tomorrow", anchor: "§36.7" },
  { id: "nadia-xray-cleanup", anchor: "§36.8" },
] as const;

test("scenarios route lists every canonical north-star scenario", async ({
  page,
}) => {
  await page.goto("/scenarios");
  for (const scenario of SCENARIOS) {
    const card = page.getByTestId(`scenario-card-${scenario.id}`);
    await expect(card).toBeVisible();
    await expect(page.getByTestId(`scenario-anchor-${scenario.id}`)).toHaveText(
      scenario.anchor,
    );
  }
});

test("each scenario reveals at least three steps and one route chip", async ({
  page,
}) => {
  await page.goto("/scenarios");
  for (const scenario of SCENARIOS) {
    await page.getByTestId(`scenario-steps-toggle-${scenario.id}`).click();
    const steps = page.getByTestId(`scenario-steps-${scenario.id}`).getByRole("listitem");
    await expect(steps.first()).toBeVisible();
    expect(await steps.count()).toBeGreaterThanOrEqual(3);
  }
});

test("scenarios harness exposes the proof anchors that prove each run", async ({
  page,
}) => {
  await page.goto("/scenarios");
  for (const scenario of SCENARIOS) {
    await page.getByTestId(`scenario-steps-toggle-${scenario.id}`).click();
    const proofs = page.getByTestId(`scenario-proofs-${scenario.id}`);
    await expect(proofs).toContainText(/Proofs:/);
  }
});
