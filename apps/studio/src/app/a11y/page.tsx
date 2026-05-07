"use client";

import { useEffect, useState } from "react";

import {
  DiffLine,
  KeyboardCheatsheet,
  LanguagePicker,
  SkipLink,
  StatusGlyph,
} from "@/components/__a11y__";
import { STATUS_VARIANTS } from "@/lib/a11y";
import { ensureLanguageLoaded, type Language } from "@/lib/i18n";

const LOCALISED_HEADING: Record<Language, string> = {
  en: "Accessibility, i18n and color-blind safety",
  es: "Accesibilidad, i18n y daltonismo seguro",
  de: "Barrierefreiheit, i18n und Farbenblindheits-Sicherheit",
  fr: "Accessibilité, i18n et sécurité daltonienne",
  ja: "アクセシビリティ、i18n、色覚多様性の安全性",
};

const LOCALISED_PICKER: Record<Language, string> = {
  en: "Language",
  es: "Idioma",
  de: "Sprache",
  fr: "Langue",
  ja: "言語",
};

const LOCALISED_SKIP: Record<Language, string> = {
  en: "Skip to main content",
  es: "Saltar al contenido principal",
  de: "Zum Hauptinhalt springen",
  fr: "Aller au contenu principal",
  ja: "メインコンテンツへスキップ",
};

export default function AccessibilityDemoPage(): JSX.Element {
  const [language, setLanguage] = useState<Language>("en");

  useEffect(() => {
    ensureLanguageLoaded(language).catch(() => {
      // Lazy locale bundles are best-effort in the demo route.
    });
  }, [language]);

  return (
    <>
      <SkipLink targetId="a11y-main" label={LOCALISED_SKIP[language]} />
      <main
        id="a11y-main"
        aria-label="Accessibility demo"
        className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6"
      >
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold" data-testid="a11y-heading">
              {LOCALISED_HEADING[language]}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Status, diffs and shortcuts on this page never depend on colour
              alone (§30.4) and the entire surface is reachable by keyboard
              (§30.1).
            </p>
          </div>
          <LanguagePicker
            current={language}
            onChange={setLanguage}
            label={LOCALISED_PICKER[language]}
          />
        </header>

        <section
          aria-label="Status indicators"
          data-testid="status-grid"
          className="grid grid-cols-2 gap-3 sm:grid-cols-3"
        >
          {STATUS_VARIANTS.map((variant) => (
            <div
              key={variant}
              className="rounded-md border border-border bg-card p-3"
            >
              <StatusGlyph variant={variant} />
            </div>
          ))}
        </section>

        <section
          aria-label="Diff sample"
          className="rounded-md border border-border bg-card p-4"
        >
          <h2 className="text-base font-semibold">Diff sample</h2>
          <div className="mt-2 space-y-1">
            <DiffLine kind="unchanged">retrieval.k = 8</DiffLine>
            <DiffLine kind="removed">retrieval.rerank = false</DiffLine>
            <DiffLine kind="added">retrieval.rerank = true</DiffLine>
            <DiffLine kind="added">
              {'retrieval.rerank.model = "loop-reranker-v2"'}
            </DiffLine>
          </div>
        </section>

        <KeyboardCheatsheet />
      </main>
    </>
  );
}
