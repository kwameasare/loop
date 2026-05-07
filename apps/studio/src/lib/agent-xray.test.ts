import { describe, expect, it, vi } from "vitest";

import { buildAgentXrayModel, fetchAgentXrayTraces } from "./agent-xray";
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

describe("fetchAgentXrayTraces", () => {
  it("loads recent trace summaries and resolves their details", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/workspaces/ws-1/traces")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                workspace_id: "ws-1",
                trace_id: "f".repeat(32),
                turn_id: "11111111-1111-4111-8111-111111111111",
                conversation_id: "22222222-2222-4222-8222-222222222222",
                agent_id: "33333333-3333-4333-8333-333333333333",
                started_at: "2026-05-07T12:00:00Z",
                duration_ms: 100,
                span_count: 1,
                error: false,
              },
            ],
            next_cursor: null,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          trace_id: "f".repeat(32),
          turn_id: "11111111-1111-4111-8111-111111111111",
          conversation_id: "22222222-2222-4222-8222-222222222222",
          agent_id: "33333333-3333-4333-8333-333333333333",
          started_at: "2026-05-07T12:00:00Z",
          duration_ms: 100,
          span_count: 1,
          error: false,
          spans: [
            {
              span_id: "span-1",
              parent_span_id: null,
              kind: "channel",
              name: "runtime turn",
              started_at: "2026-05-07T12:00:00Z",
              latency_ms: 100,
              cost_usd: 0,
              status: "ok",
              attrs: {},
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const traces = await fetchAgentXrayTraces("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(traces).toHaveLength(1);
    expect(traces[0].id).toBe("f".repeat(32));
  });
});
