import { describe, expect, it, vi } from "vitest";

import {
  QUALITY_CATEGORIES,
  QUALITY_CHECKLIST,
  SAMPLE_QUALITY_REPORTS,
  blankReview,
  fetchQualityReports,
  rollupReports,
  saveQualityReport,
  scoreScreen,
  toggleChecklistItem,
} from "./quality";

describe("scoreScreen", () => {
  it("treats every passing category as passing and counts ratio", () => {
    const fullPass = SAMPLE_QUALITY_REPORTS.find((r) =>
      r.screen.includes("workbench"),
    )!;
    const score = scoreScreen(fullPass);
    expect(score.failing).toEqual([]);
    expect(score.passing).toEqual([...QUALITY_CATEGORIES]);
    expect(score.meetsNorthStar).toBe(true);
    expect(score.ratio).toBe(1);
    expect(score.passedItems).toBe(score.totalItems);
  });

  it("flags a screen as failing north-star when more than one category fails", () => {
    const migration = SAMPLE_QUALITY_REPORTS.find((r) =>
      r.screen.includes("migrate"),
    )!;
    const score = scoreScreen(migration);
    expect(score.failing.length).toBeGreaterThan(1);
    expect(score.meetsNorthStar).toBe(false);
    expect(score.ratio).toBeGreaterThan(0);
    expect(score.ratio).toBeLessThan(1);
  });

  it("treats a single-category failure as still north-star (§37.7)", () => {
    const trace = SAMPLE_QUALITY_REPORTS.find((r) =>
      r.screen.includes("traces"),
    )!;
    const score = scoreScreen(trace);
    expect(score.failing).toEqual(["precision"]);
    expect(score.meetsNorthStar).toBe(true);
  });
});

describe("rollupReports", () => {
  it("counts north-star meeting screens and per-category failures", () => {
    const r = rollupReports(SAMPLE_QUALITY_REPORTS);
    expect(r.totalScreens).toBe(3);
    expect(r.meetingNorthStar).toBe(2);
    // migration screen fails clarity, control, friendliness, enterprise-readiness
    expect(r.failingByCategory.clarity).toBe(1);
    expect(r.failingByCategory.control).toBe(1);
    expect(r.failingByCategory.friendliness).toBe(1);
    expect(r.failingByCategory["enterprise-readiness"]).toBe(1);
    expect(r.failingByCategory.delight).toBe(0);
    expect(r.reviewerCoverage["ux-thor"]).toBe(2);
  });
});

describe("blankReview + toggleChecklistItem", () => {
  it("starts every item failed, toggles a single item to passed", () => {
    const blank = blankReview("/x", "ux-thor", "2026-05-06");
    expect(scoreScreen(blank).passedItems).toBe(0);
    const after = toggleChecklistItem(blank, "cl-job");
    const score = scoreScreen(after);
    expect(score.passedItems).toBe(1);
    // toggling back returns to all-failed
    const back = toggleChecklistItem(after, "cl-job");
    expect(scoreScreen(back).passedItems).toBe(0);
  });

  it("keeps the report immutable", () => {
    const blank = blankReview("/x", "ux-thor", "2026-05-06");
    const after = toggleChecklistItem(blank, "cl-job");
    expect(after).not.toBe(blank);
    expect(scoreScreen(blank).passedItems).toBe(0);
  });
});

describe("QUALITY_CHECKLIST", () => {
  it("covers all seven categories with at least three items each", () => {
    for (const cat of QUALITY_CATEGORIES) {
      const count = QUALITY_CHECKLIST.filter((i) => i.category === cat).length;
      expect(count).toBeGreaterThanOrEqual(3);
    }
  });
});

describe("quality report client", () => {
  it("fetches reports from the control plane", async () => {
    const report = SAMPLE_QUALITY_REPORTS[0]!;
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ items: [report] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    );

    const result = await fetchQualityReports("ws-1", {
      baseUrl: "https://cp.test",
      fetcher,
      token: "tok",
    });

    expect(result).toEqual([report]);
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.test/v1/workspaces/ws-1/quality/reports");
    expect(init?.headers).toMatchObject({ authorization: "Bearer tok" });
  });

  it("saves a report to the control plane", async () => {
    const report = SAMPLE_QUALITY_REPORTS[1]!;
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify(report), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
    );

    const result = await saveQualityReport("ws-1", report, {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(result).toEqual(report);
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.test/v1/workspaces/ws-1/quality/reports");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual(report);
  });

  it("fails closed when cp-api is unavailable unless fixtures are explicitly allowed", async () => {
    await expect(fetchQualityReports("ws-1", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required",
    );

    await expect(
      fetchQualityReports("ws-1", { baseUrl: "", allowFixture: true }),
    ).resolves.toEqual([...SAMPLE_QUALITY_REPORTS]);
  });
});
