import { expect, test } from "@playwright/test";

const LANG_HEADINGS = {
  en: "Accessibility, i18n and color-blind safety",
  es: "Accesibilidad, i18n y daltonismo seguro",
  de: "Barrierefreiheit, i18n und Farbenblindheits-Sicherheit",
  fr: "Accessibilité, i18n et sécurité daltonienne",
  ja: "アクセシビリティ、i18n、色覚多様性の安全性",
} as const;

test("language picker swaps the demo heading without reload", async ({ page }) => {
  await page.goto("/a11y");
  const heading = page.getByTestId("a11y-heading");
  await expect(heading).toHaveText(LANG_HEADINGS.en);

  for (const [lang, text] of Object.entries(LANG_HEADINGS)) {
    if (lang === "en") continue;
    await page.getByTestId("language-picker-select").selectOption(lang);
    await expect(heading).toHaveText(text);
  }
});
