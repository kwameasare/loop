"use client";

import { useState } from "react";
import { ArrowRight, X } from "lucide-react";

import { SPOTLIGHT_HINTS } from "@/lib/onboarding";
import { cn } from "@/lib/utils";

export interface GuidedSpotlightProps {
  className?: string;
  /** Forever-dismiss callback. */
  onDismiss?: () => void;
  /** Initial step index, mostly for tests/storybook. */
  initialStep?: 0 | 1 | 2;
}

export function GuidedSpotlight({
  className,
  onDismiss,
  initialStep = 0,
}: GuidedSpotlightProps) {
  const [step, setStep] = useState(initialStep);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const hint = SPOTLIGHT_HINTS[step]!;
  const isLast = step === SPOTLIGHT_HINTS.length - 1;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <aside
      role="dialog"
      aria-label="First-run hint"
      data-testid="guided-spotlight"
      className={cn(
        "flex max-w-sm flex-col gap-2 rounded-md border border-border bg-card p-4 shadow-card",
        className,
      )}
    >
      <header className="flex items-center justify-between gap-2">
        <span
          className="text-[10px] uppercase tracking-wide text-muted-foreground"
          data-testid="spotlight-step"
        >
          Step {hint.step} of {SPOTLIGHT_HINTS.length}
        </span>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss spotlight forever"
          className="rounded-sm p-1 text-muted-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          data-testid="spotlight-dismiss"
        >
          <X aria-hidden="true" className="h-3 w-3" />
        </button>
      </header>
      <h3 className="text-sm font-semibold">{hint.title}</h3>
      <p className="text-xs text-muted-foreground">{hint.body}</p>
      <footer className="mt-1 flex items-center justify-between">
        <span className="flex items-center gap-1">
          {SPOTLIGHT_HINTS.map((h, i) => (
            <span
              key={h.id}
              aria-hidden="true"
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                i <= step ? "bg-foreground" : "bg-border",
              )}
            />
          ))}
        </span>
        {isLast ? (
          <button
            type="button"
            onClick={handleDismiss}
            className="rounded-md border border-border px-3 py-1 text-xs hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            data-testid="spotlight-finish"
          >
            Got it
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setStep((s) => Math.min(2, s + 1) as 0 | 1 | 2)}
            className="flex items-center gap-1 rounded-md border border-border px-3 py-1 text-xs hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            data-testid="spotlight-next"
          >
            Next
            <ArrowRight aria-hidden="true" className="h-3 w-3" />
          </button>
        )}
      </footer>
    </aside>
  );
}
