"use client";

import {
  TABLET_SURFACES,
  TABLET_SURFACE_LABELS,
  type TabletSurface,
} from "@/lib/responsive";
import { cn } from "@/lib/utils";

export interface TabletReviewPaneProps {
  className?: string;
  onOpen?: (surface: TabletSurface) => void;
}

export function TabletReviewPane({ className, onOpen }: TabletReviewPaneProps) {
  return (
    <section
      aria-label="Tablet review surfaces"
      data-testid="tablet-review-pane"
      className={cn("flex flex-col gap-3", className)}
    >
      <header>
        <h2 className="text-base font-semibold">Review and approval</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Tablet mode (§31.2) is a two-pane layout for review, approval, and
          parity audit. Editing happens on desktop.
        </p>
      </header>
      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {TABLET_SURFACES.map((s) => (
          <li key={s}>
            <button
              type="button"
              onClick={() => onOpen?.(s)}
              data-testid={`tablet-surface-${s}`}
              className="flex w-full items-center justify-between rounded-md border border-border bg-card p-3 text-left text-sm hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              {TABLET_SURFACE_LABELS[s]}
              <span aria-hidden="true">›</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
