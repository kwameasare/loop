"use client";

import { useSettings } from "@/lib/use-settings";

export function ThemeRuntime() {
  useSettings();
  return null;
}
