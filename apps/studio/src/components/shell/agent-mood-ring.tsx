"use client";

import { AgentGlassOrb } from "@/components/agents/agent-glass-orb";
import { cn } from "@/lib/utils";

export type AgentMood = "healthy" | "drifting" | "degrading" | "incident";

const MOOD_STATE: Record<
  AgentMood,
  "healthy" | "drifting" | "degraded" | "blocked"
> = {
  healthy: "healthy",
  drifting: "drifting",
  degrading: "degraded",
  incident: "blocked",
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
      className={cn("inline-flex", "h-6 w-6")}
      data-testid="agent-mood-ring"
    >
      <AgentGlassOrb
        agentId={label}
        label={`${label} ambient health`}
        size="sm"
        state={MOOD_STATE[mood]}
      />
    </span>
  );
}
