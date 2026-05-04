/**
 * LanguageSwitcher component tests — S657
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  LANGUAGE_LABELS,
  SUPPORTED_LANGUAGES,
} from "@/lib/i18n";
import * as i18nModule from "@/lib/i18n";

// Lightweight mock for react-i18next (must include all exports used by i18n.ts)
vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-i18next")>();
  return {
    ...actual,
    useTranslation: () => ({
      i18n: { language: "en" },
    }),
  };
});

import { LanguageSwitcher } from "@/components/shell/language-switcher";

describe("LanguageSwitcher", () => {
  it("renders a select element with aria-label", () => {
    render(<LanguageSwitcher />);
    expect(screen.getByRole("combobox", { name: /select language/i })).toBeDefined();
  });

  it("renders an option for every supported language", () => {
    render(<LanguageSwitcher />);
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(screen.getByText(LANGUAGE_LABELS[lang])).toBeDefined();
    }
  });

  it("calls setLanguage when a new option is selected", () => {
    const setLanguageSpy = vi
      .spyOn(i18nModule, "setLanguage")
      .mockResolvedValue(undefined);
    render(<LanguageSwitcher />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "fr" } });
    expect(setLanguageSpy).toHaveBeenCalledWith("fr");
  });
});
