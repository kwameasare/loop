import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "@/locales/en/common.json";

export const SUPPORTED_LANGUAGES = ["en", "es", "de", "fr", "ja"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "English",
  es: "Español",
  de: "Deutsch",
  fr: "Français",
  ja: "日本語",
};

const resources = {
  en: { common: enCommon },
};

const localeLoaders: Record<Exclude<Language, "en">, () => Promise<unknown>> = {
  es: () => import("@/locales/es/common.json"),
  de: () => import("@/locales/de/common.json"),
  fr: () => import("@/locales/fr/common.json"),
  ja: () => import("@/locales/ja/common.json"),
};

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources,
    lng: "en",
    fallbackLng: "en",
    defaultNS: "common",
    interpolation: {
      escapeValue: false, // React already escapes
    },
  });
}

export async function ensureLanguageLoaded(lang: Language): Promise<void> {
  if (lang === "en") return;
  if (i18n.hasResourceBundle(lang, "common")) return;

  const loaded = await localeLoaders[lang]();
  const common =
    loaded && typeof loaded === "object" && "default" in loaded
      ? (loaded as { default: unknown }).default
      : loaded;

  i18n.addResourceBundle(lang, "common", common, true, true);
}

export async function setLanguage(lang: Language): Promise<void> {
  await ensureLanguageLoaded(lang);
  await i18n.changeLanguage(lang);
}

export default i18n;
