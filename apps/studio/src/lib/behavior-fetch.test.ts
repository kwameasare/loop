import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchBehaviorEditorData } from "@/lib/behavior";

function versionResponse() {
  return Response.json({
    items: [
      {
        id: "ver_1",
        agent_id: "agent_support",
        version: 1,
        created_at: "2026-05-09T10:00:00Z",
        spec: {
          deploy_state: "active",
          eval_status: "passed",
          system_prompt: "Answer refund questions. Escalate legal threats.",
          tools: ["lookup_order"],
          promoted_to: "production",
        },
      },
    ],
  });
}

describe("fetchBehaviorEditorData", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;
  const previousPublicBaseUrl = process.env.NEXT_PUBLIC_LOOP_API_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    if (previousPublicBaseUrl === undefined) delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    else process.env.NEXT_PUBLIC_LOOP_API_URL = previousPublicBaseUrl;
  });

  it("returns a degraded empty model instead of fixture behavior without cp-api", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    const data = await fetchBehaviorEditorData("agent_support");

    expect(data.sections).toEqual([]);
    expect(data.degradedReason).toMatch(/control-plane versions endpoint/i);
    expect(data.agentName).toBe("Agent agent_support");
  });

  it("marks sentence telemetry as unavailable when cp-api has no telemetry evidence", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/versions")) return versionResponse();
      return new Response("missing", { status: 404 });
    });

    const data = await fetchBehaviorEditorData("agent_support", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });

    expect(data.sections[0]?.sentences[0]?.telemetry).toMatchObject({
      evidence:
        "No evidence yet. Run replay, create evals, or sample production safely.",
      confidence: "unsupported",
      citedOutputs7d: 0,
    });
    expect(data.riskFlags).toEqual([]);
    expect(data.evalEvidence).toBe("cp-api version ver_1; eval status passed");
  });

  it("hydrates behavior sentence telemetry from live cp-api evidence", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/versions")) return versionResponse();
      return Response.json({
        items: [
          {
            sentence_id: "live_sentence_1_1",
            cited_outputs_7d: 47,
            contradicted_traces: 3,
            never_invoked_turns: 412,
            eval_cases: 9,
            confidence: "high",
            representative_traces: ["trace_1", "trace_2"],
          },
        ],
      });
    });

    const data = await fetchBehaviorEditorData("agent_support", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });

    expect(data.sections[0]?.sentences[0]?.telemetry).toMatchObject({
      citedOutputs7d: 47,
      contradictedTraces: 3,
      neverInvokedTurns: 412,
      evalCases: 9,
      evidence: "trace_1, trace_2",
      confidence: "high",
    });
  });

  it("derives live risk flags from the version instead of fixture-era claims", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/versions")) {
        return Response.json({
          items: [
            {
              id: "ver_risky",
              agent_id: "agent_support",
              version: 2,
              created_at: "2026-05-09T11:00:00Z",
              spec: {
                deploy_state: "inactive",
                eval_status: "failed",
                system_prompt:
                  "Remember support preferences. Never store payment data or secrets.",
                tools: ["issue_refund"],
              },
            },
          ],
        });
      }
      return new Response("missing", { status: 404 });
    });

    const data = await fetchBehaviorEditorData("agent_support", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });

    expect(data.riskFlags.map((flag) => flag.id)).toEqual([
      "risk_eval_gap",
      "risk_tool_grant",
      "risk_memory_boundary",
    ]);
    expect(data.riskFlags.map((flag) => flag.evidence).join(" ")).toContain(
      "cp-api version ver_risky",
    );
    expect(data.riskFlags.map((flag) => flag.evidence).join(" ")).not.toContain(
      "eval_refunds case refund_window_es_may",
    );
    expect(data.preview.canApply).toBe(false);
  });
});
