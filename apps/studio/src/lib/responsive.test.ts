import { describe, expect, it } from "vitest";

import {
  LARGE_DISPLAY_SURFACES,
  MODE_ACTION_ALLOWLIST,
  SECOND_MONITOR_PANES,
  TABLET_SURFACES,
  URGENT_ACTIONS,
  gateAction,
  isActionAllowed,
  modeForViewport,
} from "./responsive";

describe("modeForViewport", () => {
  it("classifies viewports by canonical breakpoints", () => {
    expect(modeForViewport(360)).toBe("mobile");
    expect(modeForViewport(900)).toBe("tablet");
    expect(modeForViewport(1440)).toBe("desktop");
    expect(modeForViewport(2560)).toBe("large-display");
  });
});

describe("MODE_ACTION_ALLOWLIST", () => {
  it("never permits full edit actions on mobile (§31.3)", () => {
    const banned = ["edit-agent", "edit-policy", "edit-kb", "open-workbench"] as const;
    for (const a of banned) {
      expect(MODE_ACTION_ALLOWLIST.mobile.includes(a)).toBe(false);
    }
    // every urgent action must be reachable on mobile
    for (const a of URGENT_ACTIONS) {
      expect(MODE_ACTION_ALLOWLIST.mobile.includes(a)).toBe(true);
    }
  });

  it("tablet adds review surfaces but not the full editor", () => {
    expect(MODE_ACTION_ALLOWLIST.tablet.includes("approvals")).toBe(true);
    expect(MODE_ACTION_ALLOWLIST.tablet.includes("parity-report")).toBe(true);
    expect(MODE_ACTION_ALLOWLIST.tablet.includes("edit-agent")).toBe(false);
  });

  it("desktop unlocks command palette and multiplayer", () => {
    expect(MODE_ACTION_ALLOWLIST.desktop.includes("command-palette")).toBe(true);
    expect(MODE_ACTION_ALLOWLIST.desktop.includes("multiplayer-cursor")).toBe(true);
    expect(MODE_ACTION_ALLOWLIST.desktop.includes("edit-agent")).toBe(true);
  });
});

describe("gateAction", () => {
  it("allows urgent actions on mobile", () => {
    const r = gateAction(320, "rollback");
    expect(r.allowed).toBe(true);
    expect(r.mode).toBe("mobile");
  });

  it("refuses full editing on mobile and gives a next step", () => {
    const r = gateAction(320, "edit-agent");
    expect(r.allowed).toBe(false);
    expect(r.reason).toMatch(/§31\.3/);
    expect(r.suggestion).toMatch(/desktop/i);
  });

  it("refuses palette on tablet but accepts approvals", () => {
    expect(gateAction(900, "command-palette").allowed).toBe(false);
    expect(gateAction(900, "approvals").allowed).toBe(true);
  });
});

describe("isActionAllowed", () => {
  it("matches the allowlist", () => {
    expect(isActionAllowed("desktop", "edit-agent")).toBe(true);
    expect(isActionAllowed("mobile", "edit-policy")).toBe(false);
  });
});

describe("surface registries", () => {
  it("exposes the canonical second-monitor four panes", () => {
    expect(SECOND_MONITOR_PANES).toEqual([
      "timeline",
      "production-tail",
      "inbox",
      "deploy-health",
    ]);
  });

  it("exposes the canonical large-display five surfaces", () => {
    expect(LARGE_DISPLAY_SURFACES).toHaveLength(5);
  });

  it("exposes the canonical tablet five surfaces", () => {
    expect(TABLET_SURFACES).toHaveLength(5);
  });
});
