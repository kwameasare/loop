import { describe, expect, it } from "vitest";

import {
  IMPORT_WIZARD_STEPS,
  MIGRATION_ENTRY_CHOICES,
  MIGRATION_SOURCES,
  REVIEW_ITEMS,
  countReviewItemsBySeverity,
  findWizardStep,
  wizardStepStates,
} from "./migration";

describe("migration model", () => {
  it("treats import as the only first-class entry choice", () => {
    const firstClass = MIGRATION_ENTRY_CHOICES.filter((c) => c.firstClass);
    expect(firstClass).toHaveLength(1);
    expect(firstClass[0]?.id).toBe("import");
    expect(MIGRATION_ENTRY_CHOICES.map((c) => c.id)).toEqual([
      "import",
      "template",
      "git",
      "blank",
    ]);
  });

  it("labels every source as verified, planned, or aspirational", () => {
    const allowed = new Set(["verified", "planned", "aspirational"]);
    for (const source of MIGRATION_SOURCES) {
      expect(allowed.has(source.status)).toBe(true);
    }
    // Botpress is the canonical verified source for the launch list.
    const botpress = MIGRATION_SOURCES.find((s) => s.id === "botpress");
    expect(botpress?.status).toBe("verified");
  });

  it("does not over-promise platform support", () => {
    const aspirationalIds = new Set(
      MIGRATION_SOURCES.filter((s) => s.status === "aspirational").map((s) => s.id),
    );
    // Aspirational sources must include the partnerships called out in §18.2
    // so marketing can never accidentally promote them as verified.
    expect(aspirationalIds.has("chatbase-fin-sierra")).toBe(true);
    expect(aspirationalIds.has("n8n-zapier")).toBe(true);
  });

  it("walks the canonical nine-step import wizard in order", () => {
    expect(IMPORT_WIZARD_STEPS).toHaveLength(9);
    expect(IMPORT_WIZARD_STEPS.map((s) => s.id)).toEqual([
      "choose-source",
      "upload-or-connect",
      "analyze",
      "inventory",
      "map",
      "resolve-gaps",
      "generate",
      "prove-parity",
      "stage-cutover",
    ]);
    IMPORT_WIZARD_STEPS.forEach((step, idx) => {
      expect(step.index).toBe(idx + 1);
    });
  });

  it("computes step states without lying about future progress", () => {
    const states = wizardStepStates("map");
    const byId = Object.fromEntries(states.map((s) => [s.id, s.state]));
    expect(byId["choose-source"]).toBe("production");
    expect(byId["analyze"]).toBe("production");
    expect(byId["map"]).toBe("canary");
    expect(byId["resolve-gaps"]).toBe("draft");
    expect(byId["stage-cutover"]).toBe("draft");
  });

  it("rejects unknown wizard step ids", () => {
    expect(() =>
      findWizardStep("nonsense" as unknown as Parameters<typeof findWizardStep>[0]),
    ).toThrow();
  });

  it("counts review items by severity for the middle pane summary", () => {
    const counts = countReviewItemsBySeverity(REVIEW_ITEMS);
    expect(counts.blocking).toBeGreaterThanOrEqual(1);
    expect(counts.advisory + counts.fyi + counts.blocking).toBe(REVIEW_ITEMS.length);
  });

  it("preserves source ids on every review item for lineage", () => {
    for (const item of REVIEW_ITEMS) {
      expect(item.sourceId).toMatch(/\./); // namespaced legacy id
    }
  });
});
