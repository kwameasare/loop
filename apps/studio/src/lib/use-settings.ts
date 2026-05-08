"use client";

/**
 * S155: ``useSettings()`` -- profile name, region, and theme.
 *
 * Stores profile name override and theme preference in localStorage so
 * they survive page reloads. Region is derived from ``inferRegion()``
 * at mount time and treated as read-only in the UI (workspace region
 * cannot be changed after creation).
 *
 * Keys:
 *   loop.settings.profileName  -- string
 *   loop.settings.theme        -- "light" | "dark" | "system"
 */

import { useCallback, useEffect, useState } from "react";
import { inferRegion } from "@/lib/regions";
import type { RegionName } from "@/lib/openapi-types";

export type Theme = "light" | "dark" | "system";

const KEY_PROFILE = "loop.settings.profileName";
const KEY_THEME = "loop.settings.theme";
const DEFAULT_THEME: Theme = "dark";

function readStorage(key: string): string | null {
  if (typeof localStorage === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch {
    // Silently ignore (private-browsing quota, etc.)
  }
}

function prefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return true;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme === "system") return prefersDark() ? "dark" : "light";
  return theme;
}

export function applyThemePreference(theme: Theme): void {
  if (typeof document === "undefined") return;
  const resolved = resolveTheme(theme);
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
}

export interface SettingsState {
  profileName: string;
  region: RegionName;
  theme: Theme;
  setProfileName: (name: string) => void;
  setTheme: (theme: Theme) => void;
}

export function useSettings(defaultProfileName = ""): SettingsState {
  const [profileName, setProfileNameState] = useState<string>(() => {
    return readStorage(KEY_PROFILE) ?? defaultProfileName;
  });

  const [theme, setThemeState] = useState<Theme>(() => {
    return DEFAULT_THEME;
  });

  const [region, setRegion] = useState<RegionName>("na-east");

  useEffect(() => {
    setRegion(inferRegion());
  }, []);

  useEffect(() => {
    const stored = readStorage(KEY_THEME);
    if (stored === "light" || stored === "dark" || stored === "system") {
      setThemeState(stored);
      applyThemePreference(stored);
      return;
    }
    applyThemePreference(DEFAULT_THEME);
  }, []);

  useEffect(() => {
    applyThemePreference(theme);
    if (
      theme !== "system" ||
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystemTheme = () => applyThemePreference("system");
    media.addEventListener?.("change", syncSystemTheme);
    return () => media.removeEventListener?.("change", syncSystemTheme);
  }, [theme]);

  const setProfileName = useCallback((name: string) => {
    setProfileNameState(name);
    writeStorage(KEY_PROFILE, name);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    writeStorage(KEY_THEME, t);
    applyThemePreference(t);
    window.dispatchEvent(new CustomEvent("loop:theme-change", { detail: t }));
  }, []);

  return { profileName, region, theme, setProfileName, setTheme };
}
