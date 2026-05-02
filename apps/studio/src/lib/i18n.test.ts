/**
 * i18n scaffolding tests — S657 ga-polish
 *
 * Validates the i18n configuration, translation coverage, and
 * language-switcher component.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  LANGUAGE_LABELS,
  SUPPORTED_LANGUAGES,
  type Language,
} from "@/lib/i18n";

// ── Module exports ────────────────────────────────────────────────────────

describe("i18n module", () => {
  it("exports exactly 5 supported languages", () => {
    expect(SUPPORTED_LANGUAGES).toHaveLength(5);
  });

  it("supports en, es, de, fr, ja", () => {
    const langs: Language[] = ["en", "es", "de", "fr", "ja"];
    for (const lang of langs) {
      expect(SUPPORTED_LANGUAGES).toContain(lang);
    }
  });

  it("en is the first entry (source language)", () => {
    expect(SUPPORTED_LANGUAGES[0]).toBe("en");
  });

  it("LANGUAGE_LABELS has a label for every supported language", () => {
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(LANGUAGE_LABELS[lang], `label for ${lang}`).toBeDefined();
      expect(LANGUAGE_LABELS[lang].length).toBeGreaterThan(0);
    }
  });

  it("English label is 'English'", () => {
    expect(LANGUAGE_LABELS["en"]).toBe("English");
  });
});

// ── Translation file coverage ─────────────────────────────────────────────

const LOCALES_DIR = join(__dirname, "..", "locales");

function loadLocale(lang: string) {
  const path = join(LOCALES_DIR, lang, "common.json");
  return JSON.parse(readFileSync(path, "utf-8"));
}

describe("translation file coverage", () => {
  const enKeys = Object.keys(loadLocale("en")).flatMap((ns) =>
    Object.keys(loadLocale("en")[ns]).map((k) => `${ns}.${k}`)
  );

  const otherLangs: Language[] = ["es", "de", "fr", "ja"];

  for (const lang of otherLangs) {
    it(`${lang}/common.json has all top-level namespaces from en`, () => {
      const enData = loadLocale("en");
      const langData = loadLocale(lang);
      for (const ns of Object.keys(enData)) {
        expect(langData, `${lang} missing namespace ${ns}`).toHaveProperty(ns);
      }
    });

    it(`${lang}/common.json has all keys from en`, () => {
      const enData = loadLocale("en");
      const langData = loadLocale(lang);
      for (const ns of Object.keys(enData)) {
        for (const key of Object.keys(enData[ns])) {
          expect(
            langData[ns],
            `${lang}.${ns}.${key} must exist`
          ).toHaveProperty(key);
        }
      }
    });
  }

  it("en has nav, actions, auth, errors namespaces", () => {
    const enData = loadLocale("en");
    expect(enData).toHaveProperty("nav");
    expect(enData).toHaveProperty("actions");
    expect(enData).toHaveProperty("auth");
    expect(enData).toHaveProperty("errors");
  });
});

// ── i18n initialisation ───────────────────────────────────────────────────

describe("i18n initialisation", () => {
  it("initialises without error and default lang is en", async () => {
    const { default: i18n } = await import("@/lib/i18n");
    expect(i18n.language).toBe("en");
  });

  it("can look up a key in the default (en) language", async () => {
    const { default: i18n } = await import("@/lib/i18n");
    expect(i18n.t("actions.save")).toBe("Save");
  });

  it("can look up a key after switching to es", async () => {
    const { default: i18n } = await import("@/lib/i18n");
    await i18n.changeLanguage("es");
    expect(i18n.t("actions.save")).toBe("Guardar");
    await i18n.changeLanguage("en"); // reset
  });

  it("falls back to en for unknown language", async () => {
    const { default: i18n } = await import("@/lib/i18n");
    await i18n.changeLanguage("xx");
    expect(i18n.t("actions.save")).toBe("Save");
    await i18n.changeLanguage("en"); // reset
  });
});
