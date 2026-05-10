import { describe, expect, it, vi } from "vitest";

import {
  EVAL_RUN_DETAIL_CP_API_REQUIRED,
  EVAL_SUITE_DETAIL_CP_API_REQUIRED,
  createEvalSuite,
  diffAgainstBaseline,
  formatEvalUsd,
  formatPassRate,
  getEvalFoundryModel,
  getEvalRun,
  getEvalSuite,
  listEvalSuites,
  resultDiffForRun,
  triggerEvalSuiteRun,
  type EvalRunDetail,
} from "./evals";

describe("listEvalSuites", () => {
  it("returns degraded state when no baseUrl is configured", async () => {
    const { items, degraded_reason } = await listEvalSuites();
    expect(items).toEqual([]);
    expect(degraded_reason).toMatch(/LOOP_CP_API_BASE_URL is required/);
  });

  it("returns fixture suites only when explicitly allowed", async () => {
    const { items } = await listEvalSuites({ allowFixture: true });
    expect(items.length).toBeGreaterThan(0);
    expect(items[0]).toMatchObject({ id: expect.stringMatching(/^evs_/) });
  });

  it("calls cp-api with auth headers when baseUrl is set", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            id: "evs_x",
            name: "x",
            agentId: "a",
            cases: 1,
            lastRunAt: null,
            passRate: null,
          },
        ],
      }),
    })) as unknown as typeof fetch;
    const { items } = await listEvalSuites({
      fetcher,
      baseUrl: "https://api.loop.dev",
      token: "tok",
      workspaceId: "ws_1",
    });
    expect(items).toHaveLength(1);
    const call = (fetcher as unknown as { mock: { calls: unknown[][] } }).mock
      .calls[0];
    expect(call[0]).toBe("https://api.loop.dev/v1/workspaces/ws_1/eval-suites");
    expect(
      (call[1] as { headers: Record<string, string> }).headers.authorization,
    ).toBe("Bearer tok");
  });

  it("does not call cp-api without workspace context", async () => {
    const fetcher = vi.fn() as unknown as typeof fetch;
    const { items, degraded_reason } = await listEvalSuites({
      fetcher,
      baseUrl: "https://api.loop.dev",
    });
    expect(items).toEqual([]);
    expect(degraded_reason).toMatch(/Workspace context is required/);
    expect(fetcher).not.toHaveBeenCalled();
  });
});

describe("getEvalSuite / getEvalRun", () => {
  it("requires cp-api for suite details unless fixture mode is explicit", async () => {
    await expect(getEvalSuite("evs_support_smoke")).rejects.toThrow(
      EVAL_SUITE_DETAIL_CP_API_REQUIRED,
    );
  });

  it("fixture mode returns suite with two runs and pass rate", async () => {
    const detail = await getEvalSuite("evs_support_smoke", {
      allowFixture: true,
    });
    expect(detail).not.toBeNull();
    expect(detail!.runs).toHaveLength(2);
    expect(detail!.runs[0].baselineRunId).toBe(detail!.runs[1].id);
  });

  it("marks live suite-detail 404 as degraded evidence instead of not found", async () => {
    const fetcher = vi.fn(async () => ({
      ok: false,
      status: 404,
      json: async () => ({}),
    })) as unknown as typeof fetch;
    await expect(
      getEvalSuite("missing", {
        fetcher,
        baseUrl: "https://api.loop.dev",
      }),
    ).rejects.toThrow(/eval suite detail route returned 404/i);
  });

  it("maps live suite details from the control-plane suite detail route", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        id: "evs_live",
        name: "Live suite",
        dataset_ref: "agent:agent_live:evals/live",
        cases: 3,
        last_run_at: "2026-05-09T12:00:00Z",
        pass_rate: 0.91,
        runs: [
          {
            id: "run_2",
            suite_id: "evs_live",
            state: "completed",
            started_at: "2026-05-09T12:00:00Z",
            completed_at: "2026-05-09T12:02:00Z",
            passed: 2,
            failed: 1,
            errored: 0,
            total: 3,
            baseline_run_id: "run_1",
          },
        ],
      }),
    })) as unknown as typeof fetch;

    const detail = await getEvalSuite("evs_live", {
      fetcher,
      baseUrl: "https://api.loop.dev",
    });

    expect(detail).toMatchObject({
      id: "evs_live",
      agentId: "agent_live",
      cases: 3,
      passRate: 0.91,
    });
    expect(detail?.runs[0]).toMatchObject({
      id: "run_2",
      status: "completed",
      baselineRunId: "run_1",
    });
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.loop.dev/v1/eval-suites/evs_live",
      expect.any(Object),
    );
  });

  it("getEvalRun fixture exposes per-case statuses", async () => {
    const run = await getEvalRun("evr_evs_support_smoke_002", {
      allowFixture: true,
    });
    expect(run).not.toBeNull();
    expect(run!.cases.some((c) => c.status === "fail")).toBe(true);
  });

  it("requires cp-api for run details unless fixture mode is explicit", async () => {
    await expect(getEvalRun("evr_evs_support_smoke_002")).rejects.toThrow(
      EVAL_RUN_DETAIL_CP_API_REQUIRED,
    );
  });

  it("marks live run-detail 404 as degraded evidence instead of not found", async () => {
    const fetcher = vi.fn(async () => ({
      ok: false,
      status: 404,
      json: async () => ({}),
    })) as unknown as typeof fetch;

    await expect(
      getEvalRun("missing", {
        fetcher,
        baseUrl: "https://api.loop.dev",
      }),
    ).rejects.toThrow(/eval run detail route returned 404/i);
  });

  it("maps live run details from the control-plane run route", async () => {
    const fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        id: "run_live",
        suite_id: "evs_live",
        state: "pending",
        started_at: "2026-05-09T12:00:00Z",
        completed_at: null,
        passed: 0,
        failed: 0,
        errored: 0,
        total: 0,
        cases: [],
      }),
    })) as unknown as typeof fetch;

    const run = await getEvalRun("run_live", {
      fetcher,
      baseUrl: "https://api.loop.dev",
    });

    expect(run).toMatchObject({
      id: "run_live",
      suiteId: "evs_live",
      status: "queued",
      cases: [],
    });
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.loop.dev/v1/eval-runs/run_live",
      expect.any(Object),
    );
  });
});

describe("diffAgainstBaseline", () => {
  it("flags regressions, recoveries and new cases", () => {
    const current: EvalRunDetail = {
      id: "r2",
      suiteId: "s",
      status: "completed",
      startedAt: "",
      finishedAt: null,
      passed: 1,
      failed: 1,
      errored: 0,
      total: 3,
      baselineRunId: "r1",
      cases: [
        {
          caseId: "a",
          name: "a",
          status: "fail",
          expected: "",
          actual: "",
          baselineStatus: "pass",
          durationMs: 0,
        },
        {
          caseId: "b",
          name: "b",
          status: "pass",
          expected: "",
          actual: "",
          baselineStatus: "fail",
          durationMs: 0,
        },
        {
          caseId: "c",
          name: "c",
          status: "pass",
          expected: "",
          actual: "",
          baselineStatus: null,
          durationMs: 0,
        },
      ],
    };
    const baseline: EvalRunDetail = {
      ...current,
      id: "r1",
      baselineRunId: null,
      cases: [
        {
          caseId: "a",
          name: "a",
          status: "pass",
          expected: "",
          actual: "",
          baselineStatus: null,
          durationMs: 0,
        },
        {
          caseId: "b",
          name: "b",
          status: "fail",
          expected: "",
          actual: "",
          baselineStatus: null,
          durationMs: 0,
        },
      ],
    };
    const diff = diffAgainstBaseline(current, baseline);
    expect(diff.find((d) => d.caseId === "a")!.kind).toBe("regression");
    expect(diff.find((d) => d.caseId === "b")!.kind).toBe("recovered");
    expect(diff.find((d) => d.caseId === "c")!.kind).toBe("new");
  });

  it("treats every case as new when baseline is null", () => {
    const current: EvalRunDetail = {
      id: "r2",
      suiteId: "s",
      status: "completed",
      startedAt: "",
      finishedAt: null,
      passed: 1,
      failed: 0,
      errored: 0,
      total: 1,
      baselineRunId: null,
      cases: [
        {
          caseId: "a",
          name: "a",
          status: "pass",
          expected: "",
          actual: "",
          baselineStatus: null,
          durationMs: 0,
        },
      ],
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

describe("eval foundry model", () => {
  it("includes creation sources, suite builder controls, and featured result diffs", async () => {
    const { evidence_mode, items } = await listEvalSuites({
      allowFixture: true,
    });
    const model = getEvalFoundryModel(items, { evidenceMode: evidence_mode });
    expect(model.creationSources.map((source) => source.source)).toEqual(
      expect.arrayContaining([
        "simulator_run",
        "production_conversation",
        "human_handoff",
        "reviewer_comment",
        "migration_parity_gap",
        "knowledge_source",
        "adversarial_catch",
        "incident_cluster",
      ]),
    );
    expect(model.provenanceCases.map((item) => item.sourceType)).toEqual(
      expect.arrayContaining([
        "production_conversation",
        "reviewer_comment",
        "human_handoff",
        "migration_parity_gap",
        "incident_cluster",
      ]),
    );
    expect(model.changePackageLinks).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          changePackageRef: "change-package/cp_refund_may_042",
          evalResultsRef: "eval/run/evr_evs_support_smoke_002",
        }),
      ]),
    );
    expect(model.suiteBuilders[0]?.scorers.map((scorer) => scorer.id)).toEqual(
      expect.arrayContaining([
        "grounded_answer",
        "tool_call_assert",
        "cost_le",
      ]),
    );
    expect(model.featuredResult).toMatchObject({
      caseId: "c2",
      traceDiff: expect.stringContaining("span_answer"),
      retrievalDiff: expect.stringContaining("refund_policy_2026.pdf"),
    });
  });

  it("builds an empty suite-builder state when no suites exist", () => {
    const model = getEvalFoundryModel([]);
    expect(model.suiteBuilders).toEqual([]);
    expect(model.creationSources).toEqual([]);
    expect(model.provenanceCases).toEqual([]);
    expect(model.changePackageLinks).toEqual([]);
    expect(model.featuredResult).toBeNull();
  });

  it("does not invent provenance for live suite summaries without case evidence", () => {
    const model = getEvalFoundryModel(
      [
        {
          agentId: "agent-live",
          cases: 4,
          id: "evs_live",
          lastRunAt: null,
          name: "Live suite",
          passRate: null,
        },
      ],
      { evidenceMode: "live" },
    );

    expect(model.creationSources).toEqual([]);
    expect(model.provenanceCases).toEqual([]);
    expect(model.changePackageLinks).toEqual([]);
  });
});

describe("resultDiffForRun", () => {
  it("returns null when a run has no output evidence", () => {
    const run: EvalRunDetail = {
      id: "r",
      suiteId: "s",
      status: "completed",
      startedAt: "",
      finishedAt: null,
      passed: 1,
      failed: 0,
      errored: 0,
      total: 1,
      baselineRunId: null,
      cases: [
        {
          caseId: "a",
          name: "a",
          status: "pass",
          expected: "",
          actual: "",
          baselineStatus: null,
          durationMs: 0,
        },
      ],
    };
    expect(resultDiffForRun(run)).toBeNull();
  });
});

describe("formatEvalUsd", () => {
  it("renders signed eval cost deltas", () => {
    expect(formatEvalUsd(0.0042)).toBe("+$0.0042");
    expect(formatEvalUsd(-0.01)).toBe("-$0.01");
    expect(formatEvalUsd(0)).toBe("$0.00");
  });
});

describe("createEvalSuite", () => {
  it("requires cp-api when no baseUrl is configured", async () => {
    await expect(
      createEvalSuite({
        name: "smoke",
        dataset_ref: "datasets/support-smoke-v1",
        metrics: ["accuracy"],
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required to create eval suites");
  });

  it("returns an in-memory suite only when fixture mode is explicitly allowed", async () => {
    const created = await createEvalSuite(
      {
        name: "smoke",
        dataset_ref: "datasets/support-smoke-v1",
        metrics: ["accuracy"],
      },
      { allowFixture: true },
    );
    expect(created.name).toBe("smoke");
    expect(created.agentId).toBe("");
    expect(created.id).toMatch(/^evs_/);
  });

  it("POSTs to the workspace-scoped eval suite route when baseUrl is set", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: "evs_42",
        name: "smoke",
      }),
    });
    const created = await createEvalSuite(
      {
        name: "smoke",
        dataset_ref: "datasets/support-smoke-v1",
        metrics: ["accuracy", "latency_p95"],
      },
      { fetcher, baseUrl: "https://cp.test", workspaceId: "ws_1" },
    );
    expect(created.id).toBe("evs_42");
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws_1/eval-suites");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      name: "smoke",
      dataset_ref: "datasets/support-smoke-v1",
      metrics: ["accuracy", "latency_p95"],
    });
  });

  it("requires workspace context before posting to cp-api", async () => {
    const fetcher = vi.fn();
    await expect(
      createEvalSuite(
        {
          name: "smoke",
          dataset_ref: "datasets/support-smoke-v1",
          metrics: ["accuracy"],
        },
        { fetcher, baseUrl: "https://cp.test" },
      ),
    ).rejects.toThrow(/Workspace context is required/);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("propagates non-2xx as an error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 409, json: async () => ({}) });
    await expect(
      createEvalSuite(
        {
          name: "smoke",
          dataset_ref: "datasets/support-smoke-v1",
          metrics: ["accuracy"],
        },
        { fetcher, baseUrl: "https://cp.test", workspaceId: "ws_1" },
      ),
    ).rejects.toThrow(/409/);
  });
});

describe("triggerEvalSuiteRun", () => {
  it("requires cp-api when no baseUrl is configured", async () => {
    await expect(triggerEvalSuiteRun("evs_1")).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required to trigger eval runs",
    );
  });

  it("returns in-memory run id only when fixture mode is explicitly allowed", async () => {
    const result = await triggerEvalSuiteRun("evs_1", { allowFixture: true });
    expect(result.id).toMatch(/^evr_/);
  });

  it("POSTs to /v1/eval-suites/{id}/runs", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: "evr_42" }),
    });
    const result = await triggerEvalSuiteRun("evs_1", {
      fetcher,
      baseUrl: "https://cp.test",
    });
    expect(result.id).toBe("evr_42");
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/eval-suites/evs_1/runs");
    expect(init.method).toBe("POST");
  });

  it("throws on non-2xx", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });
    await expect(
      triggerEvalSuiteRun("evs_1", {
        fetcher,
        baseUrl: "https://cp.test",
      }),
    ).rejects.toThrow(/503/);
  });
});
