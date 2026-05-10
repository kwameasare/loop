import { describe, expect, it, vi } from "vitest";

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
});
