import { describe, expect, it } from "vitest";

import {
  type FindCandidate,
  createSavedSearchStore,
  findInContext,
} from "@/lib/search";

const candidates: FindCandidate[] = [
  {
    id: "wb_refund",
    scope: "workbench",
    title: "Refund clarity",
    summary: "Drafted answer about annual renewals",
  },
  {
    id: "tr_refund",
    scope: "trace",
    title: "Refund trace t-9b23",
    summary: "Customer asked about cancellation",
  },
  {
    id: "audit_override",
    scope: "audit",
    title: "Audit override",
    summary: "Approval bypass on staging deploy",
  },
];

describe("findInContext", () => {
  it("filters by scope when one is provided", () => {
    const results = findInContext("", candidates, "trace");
    expect(results.map((r) => r.id)).toEqual(["tr_refund"]);
  });

  it("returns ranked matches across the haystack", () => {
    const results = findInContext("refund", candidates);
    expect(results.map((r) => r.id)).toContain("wb_refund");
    expect(results.map((r) => r.id)).toContain("tr_refund");
  });

  it("returns an empty list when nothing matches", () => {
    const results = findInContext("nothing-here", candidates);
    expect(results).toHaveLength(0);
  });
});

describe("createSavedSearchStore", () => {
  it("seeds with the canonical defaults", () => {
    const store = createSavedSearchStore();
    expect(store.list().length).toBeGreaterThan(0);
    expect(store.list().map((s) => s.category)).toContain("regressing-evals");
  });

  it("supports add, touch, and remove", () => {
    const store = createSavedSearchStore([]);
    store.add({
      id: "saved_x",
      name: "Custom",
      category: "audit-overrides",
      scope: "audit",
      query: "override",
    });
    expect(store.list()).toHaveLength(1);

    const touched = store.touch("saved_x", "2026-01-01T00:00:00.000Z");
    expect(touched[0]?.lastUsed).toBe("2026-01-01T00:00:00.000Z");

    const removed = store.remove("saved_x");
    expect(removed).toHaveLength(0);
  });

  it("ignores duplicate adds", () => {
    const store = createSavedSearchStore([]);
    const seed = {
      id: "saved_dup",
      name: "Dup",
      category: "failed-tools" as const,
      scope: "trace" as const,
      query: "dup",
    };
    store.add(seed);
    store.add(seed);
    expect(store.list()).toHaveLength(1);
  });
});
