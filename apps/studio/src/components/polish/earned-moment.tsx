"use client";

import { Sparkles } from "lucide-react";

import {
  EARNED_MOMENTS,
  shouldShowEarnedMoment,
  type EarnedMomentId,
  type PolishPreferences,
} from "@/lib/polish";
import { cn } from "@/lib/utils";

export interface EarnedMomentProps {
  momentId: EarnedMomentId;
  userId: string;
  objectId: string;
  /** Set of fired keys from earnedMomentKey(). The caller persists this. */
  fired: ReadonlySet<string>;
  /** Polish preferences. Falls back to silent + motion-on. */
  preferences?: Partial<PolishPreferences>;
  /** Optional context shown beneath the headline label. */
  detail?: string;
  /** Inline anchor text linking to the proof. */
  proofHref?: string;
  className?: string;
}

/**
 * Renders an EARNED moment that is rare, brief, opt-out, reduced-motion safe
 * and tied to proof (§29.7). Returns null when the moment must not fire.
 *
 * Never modal. Never blocks the next action. Always anchored to a proof URL
 * derived from the canonical `proofAnchor` field on the moment registry.
 */
export function EarnedMoment({
  momentId,
  userId,
  objectId,
  fired,
  preferences,
  detail,
  proofHref,
  className,
}: EarnedMomentProps): JSX.Element | null {
  const decision = shouldShowEarnedMoment({
    momentId,
    userId,
    objectId,
    fired,
    ...(preferences ? { preferences } : {}),
  });
  if (!decision.show) return null;
  const spec = EARNED_MOMENTS[momentId];
  return (
    <aside
      role="status"
      aria-label={spec.label}
      data-testid={`earned-moment-${momentId}`}
      data-static={decision.staticAlternative ? "true" : "false"}
      className={cn(
        "pointer-events-auto inline-flex items-center gap-2 rounded-md border",
        "border-border bg-card px-3 py-2 text-sm shadow-sm",
        decision.staticAlternative
          ? "opacity-100"
          : "transition-opacity duration-300 ease-out",
        className,
      )}
      style={
        decision.staticAlternative
          ? undefined
          : { animationDuration: `${spec.maxDurationMs}ms` }
      }
    >
      <Sparkles
        aria-hidden="true"
        className="h-4 w-4 text-focus"
        data-testid="earned-moment-glyph"
      />
      <span className="flex flex-col">
        <span className="font-medium">{spec.label}</span>
        {detail ? (
          <span className="text-xs text-muted-foreground">{detail}</span>
        ) : null}
      </span>
      <a
        data-testid="earned-moment-proof"
        href={proofHref ?? `#${spec.proofAnchor}`}
        className="text-xs text-focus underline-offset-2 hover:underline"
      >
        See proof
      </a>
    </aside>
  );
}
