"use client";

import { AMBIENT_LIFE_SOURCES, type AmbientLifeSource } from "@/lib/polish";
import { cn } from "@/lib/utils";

export interface AmbientHeartbeatProps {
  /** Real-state source. UI must not fake liveness (§29.6). */
  source: AmbientLifeSource;
  /** Last observed beat time. The component will not animate if this is null
   *  (i.e. nothing real has happened yet). */
  lastBeatAt: number | null;
  /** Force the static fallback regardless of motion preferences. */
  forceStatic?: boolean;
  /** Optional accessible label override. */
  label?: string;
  className?: string;
}

const SOURCE_LABELS: Record<AmbientLifeSource, string> = {
  "agent-heartbeat": "Agent heartbeat",
  "activity-ribbon": "Live activity",
  "now-playing-chip": "Now playing",
  "unread-notifications": "Unread notifications",
  "background-progress": "Background progress",
  "multiplayer-presence": "Collaborator presence",
};

/**
 * Renders a tiny ambient pulse anchored to a real-state source. When
 * `lastBeatAt` is null the component renders the empty (no-fake-liveness)
 * state and is silent. Reduced-motion users get a static dot.
 */
export function AmbientHeartbeat({
  source,
  lastBeatAt,
  forceStatic = false,
  label,
  className,
}: AmbientHeartbeatProps): JSX.Element {
  const live = lastBeatAt !== null;
  // Compile-time guard: only canonical ambient sources are accepted.
  void (AMBIENT_LIFE_SOURCES as readonly AmbientLifeSource[]).includes(source);
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label ?? SOURCE_LABELS[source]}
      data-testid={`ambient-${source}`}
      data-live={live ? "true" : "false"}
      className={cn(
        "inline-flex items-center gap-1.5 text-xs text-muted-foreground",
        className,
      )}
    >
      <span
        aria-hidden="true"
        data-testid={`ambient-dot-${source}`}
        data-static={forceStatic ? "true" : "false"}
        className={cn(
          "inline-block h-2 w-2 rounded-full bg-muted-foreground/60",
          live && !forceStatic && "motion-safe:animate-pulse",
          live && "bg-success/80",
        )}
      />
      {SOURCE_LABELS[source]}
    </span>
  );
}
