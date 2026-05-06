import { describe, expect, it } from "vitest";

import { buildAgentXrayModel } from "./agent-xray";
import type { Trace } from "./traces";

const trace: Trace = {
  id: "trace_refund_742",
  spans: [
    {
      id: "span_context",
      parent_id: null,
      name: "kb.retrieve.refund_policy",
      category: "retrieval",
      kind: "internal",
      service: "kb",
      start_ns: 0,
      end_ns: 100,
      status: "ok",
      attributes: { source: "refund_policy_2026.pdf", retrieved_chunks: 2 },
      events: [],
    },
    {
      id: "span_tool",
      parent_id: null,
      name: "tool.lookup_order",
      category: "tool",
      kind: "client",
      service: "tool-host",
      start_ns: 120,
      end_ns: 220,
      status: "ok",
      attributes: { tool: "lookup_order" },
      events: [],
    },
    {
      id: "span_answer",
      parent_id: null,
      name: "llm.complete",
      category: "llm",
      kind: "internal",
      service: "gateway",
      start_ns: 220,
      end_ns: 520,
      status: "ok",
      attributes: { tokens_in: 812, tokens_out: 146 },
      events: [],
      cost: {
        budget_source: "llm",
        completion_tokens: 146,
        input_usd: 0.0122,
        output_usd: 0.0254,
        prompt_tokens: 812,
        tool_usd: 0,
        total_usd: 0.0376,
      },
    },
  ],
};

describe("buildAgentXrayModel", () => {
  it("builds only trace-backed claims with representative traces", () => {
    const model = buildAgentXrayModel(trace);

    expect(model.sampleSize).toBe(1);
    expect(model.claims.map((claim) => claim.id)).toEqual(
      expect.arrayContaining([
        "xray-retrieval-policy",
        "xray-tool-lookup-order",
        "xray-cost-driver",
        "xray-no-dead-prompt-claim",
      ]),
    );
    expect(model.claims[0]?.representativeTraceIds).toContain(
      "trace_refund_742",
    );
    expect(
      model.claims.find((claim) => claim.kind === "unsupported")?.statement,
    ).toContain("cannot claim");
  });

  it("does not invent X-Ray claims for an empty sample", () => {
    const model = buildAgentXrayModel({ id: "empty", spans: [] });

    expect(model.claims).toEqual([]);
    expect(model.unsupportedReason).toContain("needs recorded spans");
  });
});
