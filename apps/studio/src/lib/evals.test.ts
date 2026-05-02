import { describe, expect, it, vi } from "vitest";

import {
  diffAgainstBaseline,
  formatPassRate,
  getEvalRun,
  getEvalSuite,
  listEvalSuites,
  type EvalRunDetail,
} from "./evals";

describe("listEvalSuites", () => {
  it("returns fixture suites when no baseUrl is configured", async () => {
    const { items } = await listEvalSuites();
    expect(items.length).toBeGreaterThan(0);
    expect(items[0]).toMatchObject({ id: expect.stringMatching(/^evs_/) });
  });

  it("calls cp-api with auth headers when baseUrl is set", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ items: [{ id: "evs_x", name: "x", agentId: "a", cases: 1, lastRunAt: null, passRate: null }] }),
    })) as unknown as typeof fetch;
    const { items } = await listEvalSuites({
      fetcher,
      baseUrl: "https://api.loop.dev",
      token: "tok",
    });
    expect(items).toHaveLength(1);
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock.calls[0];
    expect(call[0]).toBe("https://api.loop.dev/v1/evals/suites");
    expect((call[1] as { headers: Record<string, string> }).headers.authorization).toBe("Bearer tok");
  });
});

describe("getEvalSuite / getEvalRun", () => {
  it("fixture mode returns suite with two runs and pass rate", async () => {
    const detail = await getEvalSuite("evs_support_smoke");
    expect(detail).not.toBeNull();
    expect(detail!.runs).toHaveLength(2);
    expect(detail!.runs[0].baselineRunId).toBe(detail!.runs[1].id);
  });

  it("returns null when cp-api responds 404", async () => {
    const fetcher = vi.fn(async () => ({ ok: false, status: 404, json: async () => ({}) })) as unknown as typeof fetch;
    const detail = await getEvalSuite("missing", { fetcher, baseUrl: "https://api.loop.dev" });
    expect(detail).toBeNull();
  });

  it("getEvalRun fixture exposes per-case statuses", async () => {
    const run = await getEvalRun("evr_evs_support_smoke_002");
    expect(run).not.toBeNull();
    expect(run!.cases.some((c) => c.status === "fail")).toBe(true);
  });
});

describe("diffAgainstBaseline", () => {
  it("flags regressions, recoveries and new cases", () => {
    const current: EvalRunDetail = {
      id: "r2", suiteId: "s", status: "completed", startedAt: "", finishedAt: null,
      passed: 1, failed: 1, errored: 0, total: 3, baselineRunId: "r1",
      cases: [
        { caseId: "a", name: "a", status: "fail", expected: "", actual: "", baselineStatus: "pass", durationMs: 0 },
        { caseId: "b", name: "b", status: "pass", expected: "", actual: "", baselineStatus: "fail", durationMs: 0 },
        { caseId: "c", name: "c", status: "pass", expected: "", actual: "", baselineStatus: null, durationMs: 0 },
      ],
    };
    const baseline: EvalRunDetail = {
      ...current, id: "r1", baselineRunId: null,
      cases: [
        { caseId: "a", name: "a", status: "pass", expected: "", actual: "", baselineStatus: null, durationMs: 0 },
        { caseId: "b", name: "b", status: "fail", expected: "", actual: "", baselineStatus: null, durationMs: 0 },
      ],
    };
    const diff = diffAgainstBaseline(current, baseline);
    expect(diff.find((d) => d.caseId === "a")!.kind).toBe("regression");
    expect(diff.find((d) => d.caseId === "b")!.kind).toBe("recovered");
    expect(diff.find((d) => d.caseId === "c")!.kind).toBe("new");
  });

  it("treats every case as new when baseline is null", () => {
    const current: EvalRunDetail = {
      id: "r2", suiteId: "s", status: "completed", startedAt: "", finishedAt: null,
      passed: 1, failed: 0, errored: 0, total: 1, baselineRunId: null,
      cases: [{ caseId: "a", name: "a", status: "pass", expected: "", actual: "", baselineStatus: null, durationMs: 0 }],
    };
    expect(diffAgainstBaseline(current, null)[0].kind).toBe("new");
  });
});

describe("formatPassRate", () => {
  it("renders percentages with one decimal", () => {
    expect(formatPassRate(0.917)).toBe("91.7%");
    expect(formatPassRate(1)).toBe("100%");
    expect(formatPassRate(null)).toBe("—");
  });
});
