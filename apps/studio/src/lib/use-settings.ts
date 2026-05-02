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
const DEFAULT_THEME: Theme = "system";

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
    const stored = readStorage(KEY_THEME);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
    return DEFAULT_THEME;
  });

  const [region, setRegion] = useState<RegionName>("na-east");

  useEffect(() => {
    setRegion(inferRegion());
  }, []);

  const setProfileName = useCallback((name: string) => {
    setProfileNameState(name);
    writeStorage(KEY_PROFILE, name);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    writeStorage(KEY_THEME, t);
  }, []);

  return { profileName, region, theme, setProfileName, setTheme };
}
