"use client";

import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

export type AgentGlassOrbState =
  | "healthy"
  | "watching"
  | "drifting"
  | "degraded"
  | "blocked";

export type AgentGlassOrbSize = "sm" | "md" | "lg" | "xl";

const SIZE_CLASS: Record<AgentGlassOrbSize, string> = {
  sm: "h-6 w-6",
  md: "h-9 w-9",
  lg: "h-14 w-14",
  xl: "h-24 w-24",
};

const STATE_CLASS: Record<AgentGlassOrbState, string> = {
  healthy: "agent-glass-orb--healthy",
  watching: "agent-glass-orb--watching",
  drifting: "agent-glass-orb--drifting",
  degraded: "agent-glass-orb--degraded",
  blocked: "agent-glass-orb--blocked",
};

function hashSeed(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) % 360;
  }
  return hash;
}

function hueStyle(seed: string): CSSProperties {
  const base = hashSeed(seed || "loop-agent");
  return {
    "--agent-hue": `${base}`,
    "--agent-hue-2": `${(base + 78) % 360}`,
    "--agent-hue-3": `${(base + 166) % 360}`,
  } as CSSProperties;
}

export function AgentGlassOrb({
  agentId,
  label,
  size = "md",
  state = "healthy",
  className,
  decorative = false,
}: {
  agentId?: string | null;
  label: string;
  size?: AgentGlassOrbSize;
  state?: AgentGlassOrbState;
  className?: string;
  decorative?: boolean;
}): JSX.Element {
  const seed = agentId ?? label;

  return (
    <span
      className={cn(
        "agent-glass-orb",
        SIZE_CLASS[size],
        STATE_CLASS[state],
        className,
      )}
      style={hueStyle(seed)}
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : `${label} agent hue, ${state}`}
      data-testid="agent-glass-orb"
    >
      <span className="agent-glass-orb__flow" aria-hidden="true" />
      <span className="agent-glass-orb__glass" aria-hidden="true" />
      <span className="agent-glass-orb__spark" aria-hidden="true" />
      <span className="agent-glass-orb__status" aria-hidden="true" />
    </span>
  );
}
