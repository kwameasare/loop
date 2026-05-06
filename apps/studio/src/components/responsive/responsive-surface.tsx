"use client";

import {
  LARGE_DISPLAY_SURFACES,
  LARGE_DISPLAY_SURFACE_LABELS,
  RESPONSIVE_MODE_LABELS,
  type ResponsiveMode,
} from "@/lib/responsive";
import { cn } from "@/lib/utils";

import { MobileActionDeck } from "./mobile-action-deck";
import { SecondMonitor } from "./second-monitor";
import { TabletReviewPane } from "./tablet-review-pane";

export interface ResponsiveSurfaceProps {
  mode: ResponsiveMode;
  className?: string;
}

/**
 * Renders the canonical surface for a given responsive mode (§31). Used by
 * the demo route and as a reference for the shell layout switcher.
 */
export function ResponsiveSurface({ mode, className }: ResponsiveSurfaceProps) {
  return (
    <section
      data-testid={`responsive-surface-${mode}`}
      data-mode={mode}
      className={cn("flex flex-col gap-4", className)}
      aria-label={`${RESPONSIVE_MODE_LABELS[mode]} surface`}
    >
      <header>
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          {RESPONSIVE_MODE_LABELS[mode]}
        </h2>
      </header>
      {mode === "mobile" ? <MobileActionDeck /> : null}
      {mode === "tablet" ? <TabletReviewPane /> : null}
      {mode === "desktop" ? (
        <p className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground">
          Desktop mode renders the full five-region shell (sidebar, topbar,
          main editor, live preview, status footer) plus command palette and
          multiplayer cursors (§31.1).
        </p>
      ) : null}
      {mode === "large-display" ? (
        <ul
          className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3"
          data-testid="large-display-surfaces"
        >
          {LARGE_DISPLAY_SURFACES.map((s) => (
            <li
              key={s}
              data-testid={`large-display-${s}`}
              className="rounded-md border border-border bg-card p-4"
            >
              <h3 className="text-sm font-semibold">
                {LARGE_DISPLAY_SURFACE_LABELS[s]}
              </h3>
              <p className="mt-1 text-xs text-muted-foreground">
                War-room dashboard for design reviews (§31.4).
              </p>
            </li>
          ))}
        </ul>
      ) : null}
      <SecondMonitor />
    </section>
  );
}
