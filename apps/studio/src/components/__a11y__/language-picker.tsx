"use client";

import { LANGUAGE_LABELS, SUPPORTED_LANGUAGES, type Language } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export interface LanguagePickerProps {
  current: Language;
  onChange: (lang: Language) => void;
  label: string;
  className?: string;
}

/**
 * Localisation smoke surface — see e2e/a11y-localization.spec.ts. Selecting a
 * language never reloads the page; the i18n bundle is loaded lazily.
 */
export function LanguagePicker({
  current,
  onChange,
  label,
  className,
}: LanguagePickerProps): JSX.Element {
  return (
    <label
      data-testid="language-picker"
      className={cn("flex items-center gap-2 text-sm", className)}
    >
      <span className="text-muted-foreground">{label}</span>
      <select
        value={current}
        data-testid="language-picker-select"
        onChange={(event) => onChange(event.target.value as Language)}
        className="rounded-md border border-border bg-card px-2 py-1"
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {LANGUAGE_LABELS[lang]}
          </option>
        ))}
      </select>
    </label>
  );
}
