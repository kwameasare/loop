/**
 * UX406 — Creative polish primitives.
 *
 * Anchored to §29 (Motion, Tactility, Sound) and §29.7 (Earned Moments).
 * Provides:
 *   • EARNED_MOMENTS — the canonical list of rare moments and their proof
 *     anchors. Each moment fires at most once per user per relevant object.
 *   • AMBIENT_LIFE_SOURCES — the only signals that are allowed to drive
 *     ambient-life UI; everything else would be fake liveness (§29.6).
 *   • FORBIDDEN_MOTION — confetti / fireworks / shake / etc that polish must
 *     never use (§29.3). Surfaced for ESLint-style guardrails and tests.
 *   • PolishPreferences and helpers to gate sound and earned moments behind
 *     reduced-motion and the global polish-reduction switch.
 */

import { prefersReducedMotion } from "@/lib/a11y";

export const EARNED_MOMENT_IDS = [
  "first-turn",
  "first-staging-deploy",
  "first-production-promotion",
  "canary-100",
  "first-1k-production-turns",
  "migration-cutover-complete",
  "clean-eval-after-regression",
  "perfect-parity-sample",
  "first-migration-parity-threshold",
  "first-fork-beats-source",
  "first-scene-canonicalized",
  "thirty-day-pass-rate-streak",
  "first-private-skill-downstream-use",
] as const;
export type EarnedMomentId = (typeof EARNED_MOMENT_IDS)[number];

export interface EarnedMomentSpec {
  id: EarnedMomentId;
  label: string;
  /** Source of truth that proves the moment actually happened. */
  proofAnchor: string;
  /** Per-relevant-object scope. The moment fires at most once per scope+user. */
  scope: "user" | "user-and-agent" | "user-and-workspace" | "user-and-fork";
  /** Maximum on-screen duration (ms). Earned moments must be brief (§29.7). */
  maxDurationMs: number;
}

export const EARNED_MOMENTS: Record<EarnedMomentId, EarnedMomentSpec> = {
  "first-turn": {
    id: "first-turn",
    label: "First successful turn",
    proofAnchor: "trace.first_turn_id",
    scope: "user-and-agent",
    maxDurationMs: 1600,
  },
  "first-staging-deploy": {
    id: "first-staging-deploy",
    label: "First staging deploy",
    proofAnchor: "deploy.staging.changeset_id",
    scope: "user-and-agent",
    maxDurationMs: 1600,
  },
  "first-production-promotion": {
    id: "first-production-promotion",
    label: "First production promotion",
    proofAnchor: "deploy.production.changeset_id",
    scope: "user-and-agent",
    maxDurationMs: 2000,
  },
  "canary-100": {
    id: "canary-100",
    label: "Canary reached 100%",
    proofAnchor: "deploy.canary.percent",
    scope: "user-and-agent",
    maxDurationMs: 2000,
  },
  "first-1k-production-turns": {
    id: "first-1k-production-turns",
    label: "First 1,000 production turns",
    proofAnchor: "metrics.production_turns",
    scope: "user-and-agent",
    maxDurationMs: 1600,
  },
  "migration-cutover-complete": {
    id: "migration-cutover-complete",
    label: "Migration cutover complete",
    proofAnchor: "migration.cutover.id",
    scope: "user-and-workspace",
    maxDurationMs: 2000,
  },
  "clean-eval-after-regression": {
    id: "clean-eval-after-regression",
    label: "Clean eval after regression",
    proofAnchor: "eval.run_id",
    scope: "user-and-agent",
    maxDurationMs: 1600,
  },
  "perfect-parity-sample": {
    id: "perfect-parity-sample",
    label: "Perfect parity score on sample",
    proofAnchor: "parity.report_id",
    scope: "user-and-agent",
    maxDurationMs: 2000,
  },
  "first-migration-parity-threshold": {
    id: "first-migration-parity-threshold",
    label: "First migration parity at threshold",
    proofAnchor: "migration.parity.report_id",
    scope: "user-and-workspace",
    maxDurationMs: 1600,
  },
  "first-fork-beats-source": {
    id: "first-fork-beats-source",
    label: "First fork beats its source on eval",
    proofAnchor: "fork.eval.run_id",
    scope: "user-and-fork",
    maxDurationMs: 1600,
  },
  "first-scene-canonicalized": {
    id: "first-scene-canonicalized",
    label: "First scene canonicalized",
    proofAnchor: "scene.id",
    scope: "user-and-workspace",
    maxDurationMs: 1600,
  },
  "thirty-day-pass-rate-streak": {
    id: "thirty-day-pass-rate-streak",
    label: "30-day eval pass-rate streak",
    proofAnchor: "metrics.streak_days",
    scope: "user-and-agent",
    maxDurationMs: 1600,
  },
  "first-private-skill-downstream-use": {
    id: "first-private-skill-downstream-use",
    label: "First downstream use of a private skill",
    proofAnchor: "skill.first_downstream_run_id",
    scope: "user-and-workspace",
    maxDurationMs: 1600,
  },
};

export const AMBIENT_LIFE_SOURCES = [
  "agent-heartbeat",
  "activity-ribbon",
  "now-playing-chip",
  "unread-notifications",
  "background-progress",
  "multiplayer-presence",
] as const;
export type AmbientLifeSource = (typeof AMBIENT_LIFE_SOURCES)[number];

/** Motion patterns the design system FORBIDS (§29.3). Used by the polish lint
 *  test to guard regressions. */
export const FORBIDDEN_MOTION = [
  "confetti",
  "fireworks",
  "particles",
  "scroll-jacking",
  "shake-on-error",
  "childish-bounce",
  "fast-skeleton-pulse",
  "personality-spinner",
] as const;

export interface PolishPreferences {
  /** Global personal setting to reduce polish (§29.7). */
  reducePolish: boolean;
  /** Sound is silent by default (§29.8). */
  soundEnabled: boolean;
  /** OS-level reduced-motion preference. */
  reducedMotion: boolean;
}

export const DEFAULT_POLISH_PREFERENCES: PolishPreferences = {
  reducePolish: false,
  soundEnabled: false,
  reducedMotion: false,
};

/** Builds a stable scope key for the once-per-user-per-object guard. */
export function earnedMomentKey(
  userId: string,
  momentId: EarnedMomentId,
  objectId: string,
): string {
  return `earned:${userId}:${momentId}:${objectId}`;
}

export interface EarnedMomentDecision {
  /** True when the moment should render. */
  show: boolean;
  /** True when motion should be replaced with a static badge. */
  staticAlternative: boolean;
  /** True when the optional sound should play. */
  playSound: boolean;
  /** Empty when `show` is true. Otherwise explains the suppression. */
  reason?: string;
}

/**
 * Decides whether an earned moment should fire for this user+object
 * combination, given the per-user fired set and the polish preferences.
 *
 * Constraints (§29.7):
 *   • once per user per relevant object
 *   • never modal, never blocks next action — caller's responsibility
 *   • silent unless sound is enabled
 *   • reduced-motion alternative when motion is disabled
 *   • fully suppressed when the global reduce-polish toggle is on
 */
export function shouldShowEarnedMoment(input: {
  momentId: EarnedMomentId;
  userId: string;
  objectId: string;
  fired: ReadonlySet<string>;
  preferences?: Partial<PolishPreferences>;
}): EarnedMomentDecision {
  const prefs: PolishPreferences = {
    ...DEFAULT_POLISH_PREFERENCES,
    ...input.preferences,
  };
  const key = earnedMomentKey(input.userId, input.momentId, input.objectId);
  if (input.fired.has(key)) {
    return {
      show: false,
      staticAlternative: false,
      playSound: false,
      reason: "already-fired",
    };
  }
  if (prefs.reducePolish) {
    return {
      show: false,
      staticAlternative: true,
      playSound: false,
      reason: "reduce-polish",
    };
  }
  return {
    show: true,
    staticAlternative: prefs.reducedMotion,
    playSound: prefs.soundEnabled,
  };
}

/** Returns the polish preferences derived from the runtime environment. */
export function detectPolishPreferences(
  override: Partial<PolishPreferences> = {},
): PolishPreferences {
  return {
    ...DEFAULT_POLISH_PREFERENCES,
    reducedMotion: prefersReducedMotion(),
    ...override,
  };
}
