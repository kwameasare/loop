"use client";

import { Monitor, Moon, Sun } from "lucide-react";

import { useSettings, type Theme } from "@/lib/use-settings";
import { cn } from "@/lib/utils";

const NEXT_THEME: Record<Theme, Theme> = {
  dark: "light",
  light: "system",
  system: "dark",
};

const THEME_LABEL: Record<Theme, string> = {
  dark: "Dark",
  light: "Light",
  system: "System",
};

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useSettings();
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  const next = NEXT_THEME[theme];

  return (
    <button
      type="button"
      className={cn(
        "interactive-lift pressable group inline-flex h-9 items-center gap-2 rounded-md border bg-card/80 px-2.5 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur transition-all duration-swift ease-standard hover:border-info/40 hover:text-foreground",
        className,
      )}
      aria-label={`Theme: ${THEME_LABEL[theme]}. Switch to ${THEME_LABEL[next]}.`}
      title={`Theme: ${THEME_LABEL[theme]}`}
      data-testid="theme-toggle"
      onClick={() => setTheme(next)}
    >
      <Icon className="h-4 w-4 text-info transition-transform duration-swift group-hover:-rotate-6" />
      <span className="hidden sm:inline">{THEME_LABEL[theme]}</span>
    </button>
  );
}
