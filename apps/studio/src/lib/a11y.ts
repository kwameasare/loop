/**
 * UX405 — Accessibility, i18n, color-blind, keyboard sweep utilities.
 *
 * Anchored to §30 of the canonical UX standard. Provides a single source of
 * truth for:
 *   • status that is communicated via SHAPE + LABEL as well as colour (§30.4).
 *   • diff markers that survive monochrome rendering (§30.4).
 *   • the canonical keyboard-shortcut registry surfaced in the cheatsheet.
 *   • a `prefersReducedMotion()` helper used to gate decorative animation
 *     (§30.1).
 */

export const STATUS_VARIANTS = [
  "pass",
  "fail",
  "warn",
  "info",
  "pending",
  "blocked",
] as const;
export type StatusVariant = (typeof STATUS_VARIANTS)[number];

export interface StatusGlyphSpec {
  /** Single-character shape glyph. Visible to sighted users without colour. */
  glyph: string;
  /** Plain-text label exposed to screen readers and beside the glyph. */
  label: string;
  /** Tailwind-friendly tone token. Never the sole signal. */
  tone: "ok" | "danger" | "warn" | "info" | "muted";
  /** Distinct dotted/solid/etc pattern descriptor for chart strokes. */
  strokePattern: "solid" | "dashed" | "dotted" | "double" | "none";
}

/**
 * Color-independent status registry. Each variant pairs a shape, a label and
 * a stroke pattern so that achromatopsia/deuteranopia/protanopia/tritanopia
 * users still receive the signal (§30.4).
 */
export const STATUS_GLYPHS: Record<StatusVariant, StatusGlyphSpec> = {
  pass: { glyph: "●", label: "Pass", tone: "ok", strokePattern: "solid" },
  fail: { glyph: "◆", label: "Fail", tone: "danger", strokePattern: "double" },
  warn: { glyph: "▲", label: "Warning", tone: "warn", strokePattern: "dashed" },
  info: { glyph: "■", label: "Info", tone: "info", strokePattern: "dotted" },
  pending: {
    glyph: "◌",
    label: "Pending",
    tone: "muted",
    strokePattern: "dashed",
  },
  blocked: {
    glyph: "✕",
    label: "Blocked",
    tone: "danger",
    strokePattern: "none",
  },
};

export const DIFF_MARKERS = {
  added: { prefix: "+", label: "Added line", tone: "ok" as const },
  removed: { prefix: "-", label: "Removed line", tone: "danger" as const },
  unchanged: { prefix: "·", label: "Unchanged line", tone: "muted" as const },
} as const;

export type DiffKind = keyof typeof DIFF_MARKERS;

/**
 * Canonical keyboard shortcuts surfaced in the cheatsheet. Story IDs reference
 * canonical sections so that QA and docs stay in sync.
 */
export const KEYBOARD_SHORTCUTS: ReadonlyArray<{
  id: string;
  combo: string;
  scope: "global" | "canvas" | "trace" | "review";
  description: string;
  anchor: string;
}> = [
  {
    id: "skip-to-main",
    combo: "Tab",
    scope: "global",
    description: "Move focus to the Skip-to-main-content link.",
    anchor: "§30.1",
  },
  {
    id: "command-palette",
    combo: "⌘ K",
    scope: "global",
    description: "Open the command palette.",
    anchor: "§31.1",
  },
  {
    id: "list-view",
    combo: "L",
    scope: "canvas",
    description: "Toggle the canvas list view (keyboard-first).",
    anchor: "§30.2",
  },
  {
    id: "reorder-up",
    combo: "Alt + ↑",
    scope: "canvas",
    description: "Reorder selected node upwards in the list view.",
    anchor: "§30.2",
  },
  {
    id: "reorder-down",
    combo: "Alt + ↓",
    scope: "canvas",
    description: "Reorder selected node downwards in the list view.",
    anchor: "§30.2",
  },
  {
    id: "trace-table",
    combo: "T",
    scope: "trace",
    description: "Toggle the sortable span table alternative to the waterfall.",
    anchor: "§30.3",
  },
  {
    id: "trace-next",
    combo: "J",
    scope: "trace",
    description: "Move to the next span in the table.",
    anchor: "§30.3",
  },
  {
    id: "trace-prev",
    combo: "K",
    scope: "trace",
    description: "Move to the previous span in the table.",
    anchor: "§30.3",
  },
  {
    id: "approve",
    combo: "Shift + A",
    scope: "review",
    description: "Approve the focused changeset (requires confirmation).",
    anchor: "§31.3",
  },
  {
    id: "decline",
    combo: "Shift + D",
    scope: "review",
    description: "Decline the focused changeset (requires confirmation).",
    anchor: "§31.3",
  },
];

/**
 * Returns true when the user has asked the OS for reduced motion, falling back
 * to false on the server. Components must gate decorative animation behind
 * this helper (§30.1).
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Returns true when a label fits inside a target width when rendered with the
 * given pixel-per-char heuristic. Used by the localization smoke test that
 * the canonical standard requires for resize-friendly layouts (§30.1).
 */
export function fitsTargetWidth(
  label: string,
  maxWidthPx: number,
  pixelsPerChar = 8,
): boolean {
  return label.length * pixelsPerChar <= maxWidthPx;
}

/**
 * Combines status glyph + label into a screen-reader announcement. Never relies
 * on colour alone.
 */
export function announceStatus(variant: StatusVariant, context?: string): string {
  const spec = STATUS_GLYPHS[variant];
  return context ? `${spec.label}: ${context}` : spec.label;
}
