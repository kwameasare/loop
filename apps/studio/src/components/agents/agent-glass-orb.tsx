"use client";

import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

export type AgentGlassOrbState =
  | "healthy"
  | "watching"
  | "drifting"
  | "degraded"
  | "blocked";

export type AgentGlassOrbSize = "xs" | "sm" | "md" | "lg" | "xl" | "hero";

const SIZE_CLASS: Record<AgentGlassOrbSize, string> = {
  xs: "h-5 w-5",
  sm: "h-7 w-7",
  md: "h-10 w-10",
  lg: "h-16 w-16",
  xl: "h-28 w-28",
  hero: "h-64 w-64 sm:h-72 sm:w-72",
};

const STATE_CLASS: Record<AgentGlassOrbState, string> = {
  healthy: "agent-glass-orb--healthy",
  watching: "agent-glass-orb--watching",
  drifting: "agent-glass-orb--drifting",
  degraded: "agent-glass-orb--degraded",
  blocked: "agent-glass-orb--blocked",
};

function hashSeed(seed: string): number {
  let hash = 5381;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 33) ^ seed.charCodeAt(i);
  }
  return Math.abs(hash);
}

// Map an arbitrary agent seed onto our cool palette arc.
// We stay between violet (250) and cyan (200) running through blue/lavender,
// with rare excursions to magenta (300) so the gallery feels cohesive
// rather than rainbow-noisy. Each agent picks three related hues so the
// internal gradient feels chromatic but anchored.
function paletteFor(seed: string): {
  base: number;
  alt: number;
  accent: number;
} {
  const h = hashSeed(seed || "loop-agent");
  // primary band: 198..318 (cyan -> lavender -> magenta)
  const base = 198 + (h % 121);
  const alt = (base + 28 + (h % 24)) % 360;
  const accent = (base + 64 + ((h >> 3) % 18)) % 360;
  return { base, alt, accent };
}

function hueStyle(seed: string): CSSProperties {
  const { base, alt, accent } = paletteFor(seed);
  return {
    "--agent-hue": String(base),
    "--agent-hue-2": String(alt),
    "--agent-hue-3": String(accent),
  } as CSSProperties;
}

export interface AgentGlassOrbProps {
  agentId?: string | null;
  label: string;
  size?: AgentGlassOrbSize;
  state?: AgentGlassOrbState;
  className?: string;
  decorative?: boolean;
  /** Quiet the swirl — useful for dense lists. */
  quiet?: boolean;
  /** Draw a soft halo behind the orb (hero use). */
  halo?: boolean;
  /** Suppress the small status pip. */
  hideStatus?: boolean;
}

export function AgentGlassOrb({
  agentId,
  label,
  size = "md",
  state = "healthy",
  className,
  decorative = false,
  quiet = false,
  halo = false,
  hideStatus = false,
}: AgentGlassOrbProps): JSX.Element {
  const seed = agentId ?? label;
  const style = hueStyle(seed);
  // Decorative orbs (brand visuals) carry no operational state, so the
  // status pip is suppressed unless the caller explicitly opts back in.
  const showStatus = !hideStatus && !decorative;

  return (
    <span
      className={cn(
        "agent-glass-orb",
        SIZE_CLASS[size],
        STATE_CLASS[state],
        quiet && "agent-glass-orb--quiet",
        decorative && "agent-glass-orb--decorative",
        halo && "agent-glass-halo",
        className,
      )}
      style={style}
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : `${label} agent hue, ${state}`}
      data-testid="agent-glass-orb"
    >
      <span className="agent-glass-orb__flow" aria-hidden="true" />
      <span className="agent-glass-orb__caustic" aria-hidden="true" />
      <span className="agent-glass-orb__glass" aria-hidden="true" />
      <span className="agent-glass-orb__spark" aria-hidden="true" />
      {/* Local SVG mascot — next/image would not optimize an SVG
          further (it serves them as-is) and using Image with `fill`
          would conflict with our CSS mask + size animation. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/agent-mascot.svg"
        alt=""
        aria-hidden="true"
        className="agent-glass-orb__mascot"
        draggable={false}
      />
      {showStatus && (
        <span className="agent-glass-orb__status" aria-hidden="true" />
      )}
    </span>
  );
}
