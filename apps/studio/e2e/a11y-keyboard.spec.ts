import { expect, test } from "@playwright/test";

test("a11y demo route exposes a Skip-to-main-content link as the first focusable element", async ({
  page,
}) => {
  await page.goto("/a11y");
  await page.keyboard.press("Tab");
  const skip = page.getByTestId("skip-link");
  await expect(skip).toBeFocused();
  await expect(skip).toHaveAttribute("href", "#a11y-main");
});

test("status glyphs expose accessible names without colour reliance", async ({
  page,
}) => {
  await page.goto("/a11y");
  await expect(page.getByTestId("status-glyph-pass")).toHaveAttribute(
    "aria-label",
    "Pass",
  );
  await expect(page.getByTestId("status-glyph-fail")).toHaveAttribute(
    "aria-label",
    "Fail",
  );
  // Stroke pattern is also distinct so charts survive monochrome rendering.
  await expect(page.getByTestId("status-glyph-pass")).toHaveAttribute(
    "data-stroke",
    "solid",
  );
  await expect(page.getByTestId("status-glyph-fail")).toHaveAttribute(
    "data-stroke",
    "double",
  );
});

test("keyboard cheatsheet groups shortcuts by canonical scope", async ({ page }) => {
  await page.goto("/a11y");
  for (const scope of ["global", "canvas", "trace", "review"]) {
    await expect(page.getByTestId(`keyboard-scope-${scope}`)).toBeVisible();
  }
  await expect(page.getByTestId("shortcut-combo-list-view")).toBeVisible();
  await expect(page.getByTestId("shortcut-combo-trace-table")).toBeVisible();
});
