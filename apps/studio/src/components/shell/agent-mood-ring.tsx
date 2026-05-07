"use client";

import { cn } from "@/lib/utils";

export type AgentMood = "healthy" | "drifting" | "degrading" | "incident";

const MOOD_CLASS: Record<AgentMood, string> = {
  healthy: "from-success via-success to-info",
  drifting: "from-warning via-info to-warning",
  degrading: "from-warning via-warning to-destructive",
  incident: "from-destructive via-destructive to-warning",
};

export function AgentMoodRing({
  mood = "healthy",
  label,
}: {
  mood?: AgentMood;
  label: string;
}): JSX.Element {
  return (
    <span
      className={cn(
        "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br p-0.5",
        MOOD_CLASS[mood],
      )}
      aria-label={`${label} ambient health ${mood}`}
      data-testid="agent-mood-ring"
    >
      <span className="h-full w-full rounded-full bg-background" />
    </span>
  );
}
