/**
 * UX404 — Responsive modes for Studio (§31 of the canonical UX standard).
 *
 * Mode policy:
 *   - desktop: full power (five-region shell, multiplayer, palette).
 *   - tablet: review and approval only.
 *   - mobile: urgent actions only — never force full agent editing.
 *   - large-display: war rooms (observatory, deploy watch, parity board).
 *
 * "Second monitor" is a low-chrome persistent view of timeline, production
 * tail, inbox, and current deploy health (§31.4). It is orthogonal to mode.
 */

export const RESPONSIVE_MODES = [
  "desktop",
  "tablet",
  "mobile",
  "large-display",
] as const;
export type ResponsiveMode = (typeof RESPONSIVE_MODES)[number];

export const RESPONSIVE_MODE_LABELS: Record<ResponsiveMode, string> = {
  desktop: "Desktop",
  tablet: "Tablet",
  mobile: "Mobile",
  "large-display": "Large display",
};

/** Tailwind-ish breakpoint thresholds in px. */
export const RESPONSIVE_BREAKPOINTS = {
  mobileMaxPx: 640,
  tabletMaxPx: 1024,
  desktopMaxPx: 1920,
} as const;

export function modeForViewport(widthPx: number): ResponsiveMode {
  if (widthPx <= RESPONSIVE_BREAKPOINTS.mobileMaxPx) return "mobile";
  if (widthPx <= RESPONSIVE_BREAKPOINTS.tabletMaxPx) return "tablet";
  if (widthPx <= RESPONSIVE_BREAKPOINTS.desktopMaxPx) return "desktop";
  return "large-display";
}

export const URGENT_ACTIONS = [
  "ack-incident",
  "inspect-summary",
  "view-deploy",
  "approve-changeset",
  "decline-changeset",
  "rollback",
  "takeover-inbox",
  "view-cost-alert",
] as const;
export type UrgentAction = (typeof URGENT_ACTIONS)[number];

export const URGENT_ACTION_LABELS: Record<UrgentAction, string> = {
  "ack-incident": "Acknowledge incident",
  "inspect-summary": "Inspect summary",
  "view-deploy": "View deploy status",
  "approve-changeset": "Approve changeset",
  "decline-changeset": "Decline changeset",
  rollback: "Rollback",
  "takeover-inbox": "Take over inbox item",
  "view-cost-alert": "View cost alert",
};

export const TABLET_SURFACES = [
  "trace-summary",
  "cost-dashboard",
  "approvals",
  "conversation-review",
  "parity-report",
] as const;
export type TabletSurface = (typeof TABLET_SURFACES)[number];

export const TABLET_SURFACE_LABELS: Record<TabletSurface, string> = {
  "trace-summary": "Trace summary",
  "cost-dashboard": "Cost dashboard",
  approvals: "Approvals",
  "conversation-review": "Conversation review",
  "parity-report": "Parity report",
};

export const LARGE_DISPLAY_SURFACES = [
  "observatory",
  "deploy-watch",
  "parity-board",
  "live-trace-stream",
  "inbox-queue",
] as const;
export type LargeDisplaySurface = (typeof LARGE_DISPLAY_SURFACES)[number];

export const LARGE_DISPLAY_SURFACE_LABELS: Record<LargeDisplaySurface, string> = {
  observatory: "Observatory",
  "deploy-watch": "Deploy watch",
  "parity-board": "Migration parity board",
  "live-trace-stream": "Live trace stream",
  "inbox-queue": "Inbox queue",
};

export const SECOND_MONITOR_PANES = [
  "timeline",
  "production-tail",
  "inbox",
  "deploy-health",
] as const;
export type SecondMonitorPane = (typeof SECOND_MONITOR_PANES)[number];

export const SECOND_MONITOR_PANE_LABELS: Record<SecondMonitorPane, string> = {
  timeline: "Timeline",
  "production-tail": "Production tail",
  inbox: "Inbox",
  "deploy-health": "Deploy health",
};

export type GenericAction =
  | UrgentAction
  | "edit-agent"
  | "edit-policy"
  | "edit-kb"
  | "open-workbench"
  | "approvals"
  | "trace-summary"
  | "cost-dashboard"
  | "conversation-review"
  | "parity-report"
  | "command-palette"
  | "side-by-side-diff"
  | "multiplayer-cursor";

/**
 * Whitelist of actions that each responsive mode is allowed to surface.
 * Mobile NEVER includes full-edit actions per §31.3 ("Do not force full
 * agent editing onto mobile").
 */
export const MODE_ACTION_ALLOWLIST: Record<ResponsiveMode, readonly GenericAction[]> = {
  mobile: [...URGENT_ACTIONS],
  tablet: [
    ...URGENT_ACTIONS,
    "approvals",
    "trace-summary",
    "cost-dashboard",
    "conversation-review",
    "parity-report",
  ],
  desktop: [
    ...URGENT_ACTIONS,
    "approvals",
    "trace-summary",
    "cost-dashboard",
    "conversation-review",
    "parity-report",
    "edit-agent",
    "edit-policy",
    "edit-kb",
    "open-workbench",
    "command-palette",
    "side-by-side-diff",
    "multiplayer-cursor",
  ],
  "large-display": [
    ...URGENT_ACTIONS,
    "approvals",
    "trace-summary",
    "cost-dashboard",
    "conversation-review",
    "parity-report",
    "open-workbench",
  ],
};

export function isActionAllowed(mode: ResponsiveMode, action: GenericAction): boolean {
  return MODE_ACTION_ALLOWLIST[mode].includes(action);
}

/**
 * Given a viewport width and an attempted action, return either an allowed
 * surface description or a refusal explaining why and pointing to the next
 * step (§31.3).
 */
export interface ActionGateResult {
  mode: ResponsiveMode;
  allowed: boolean;
  reason?: string;
  suggestion?: string;
}

export function gateAction(widthPx: number, action: GenericAction): ActionGateResult {
  const mode = modeForViewport(widthPx);
  if (isActionAllowed(mode, action)) {
    return { mode, allowed: true };
  }
  if (mode === "mobile") {
    return {
      mode,
      allowed: false,
      reason: "Mobile mode reserves the screen for urgent actions only (§31.3).",
      suggestion: "Open Studio on a desktop to edit agents.",
    };
  }
  return {
    mode,
    allowed: false,
    reason: `Action '${action}' is not part of ${RESPONSIVE_MODE_LABELS[mode]} mode.`,
    suggestion: "Open Studio on a desktop for the full editor.",
  };
}
