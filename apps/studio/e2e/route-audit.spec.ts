import { expect, test } from "@playwright/test";

test("information architecture page surfaces every lifecycle verb", async ({
  page,
}) => {
  await page.goto("/ia");
  for (const verb of [
    "build",
    "test",
    "ship",
    "observe",
    "migrate",
    "govern",
    "onboard",
    "system",
  ]) {
    await expect(page.getByTestId(`ia-section-${verb}`)).toBeVisible();
  }
});

test("information architecture page links concrete routes", async ({
  page,
}) => {
  await page.goto("/ia");
  await expect(
    page.getByRole("link", { name: "/agents", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "/scenarios", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "/migrate", exact: true }),
  ).toBeVisible();
});

test("studio copy avoids flow-first language on the IA page", async ({
  page,
}) => {
  await page.goto("/ia");
  const body = (await page.locator("body").innerText()).toLowerCase();
  expect(body).not.toContain("flow editor");
  expect(body).not.toContain("flow-first");
  expect(body).not.toContain("mystery health");
});
