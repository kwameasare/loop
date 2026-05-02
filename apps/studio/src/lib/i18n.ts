import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "@/locales/en/common.json";
import deCommon from "@/locales/de/common.json";
import esCommon from "@/locales/es/common.json";
import frCommon from "@/locales/fr/common.json";
import jaCommon from "@/locales/ja/common.json";

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
  es: { common: esCommon },
  de: { common: deCommon },
  fr: { common: frCommon },
  ja: { common: jaCommon },
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

export default i18n;
