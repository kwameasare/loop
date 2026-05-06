"use client";

import { RESPONSIVE_MODES, RESPONSIVE_MODE_LABELS, type ResponsiveMode } from "@/lib/responsive";
import { cn } from "@/lib/utils";

export interface ResponsiveModeSwitcherProps {
  current: ResponsiveMode;
  onChange: (mode: ResponsiveMode) => void;
  className?: string;
}

/**
 * Compact mode switcher used by the responsive demo route and the shell
 * "force mode" affordance for QA. Real product code uses a viewport listener.
 */
export function ResponsiveModeSwitcher({
  current,
  onChange,
  className,
}: ResponsiveModeSwitcherProps) {
  return (
    <div
      role="tablist"
      aria-label="Responsive mode"
      data-testid="responsive-mode-switcher"
      className={cn("flex items-center gap-1 rounded-md border border-border bg-card p-1", className)}
    >
      {RESPONSIVE_MODES.map((m) => {
        const active = current === m;
        return (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={active}
            data-testid={`responsive-mode-${m}`}
            onClick={() => onChange(m)}
            className={cn(
              "rounded-sm px-2 py-1 text-xs",
              active
                ? "bg-focus/10 text-focus"
                : "text-muted-foreground hover:bg-muted/40",
            )}
          >
            {RESPONSIVE_MODE_LABELS[m]}
          </button>
        );
      })}
    </div>
  );
}
