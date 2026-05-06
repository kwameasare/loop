import { describe, expect, it } from "vitest";

import { buildTraceScrubberModel } from "./trace-scrubber";
import type { Trace } from "./traces";

const trace: Trace = {
  id: "trace_test",
  summary: {
    agent_name: "Agent",
    channel: "web",
    deploy_version: "v1",
    environment: "dev",
    eval_score: 90,
    eval_suite: "suite",
    memory_writes: 1,
    model: "gpt",
    outcome: "ok",
    provider: "OpenAI",
    retrieval_count: 1,
    snapshot_id: "snap_1",
    tool_count: 1,
    total_cost_usd: 0.03,
    total_latency_ns: 1_000,
  },
  spans: [
    {
      id: "root",
      parent_id: null,
      name: "turn",
      category: "channel",
      kind: "server",
      service: "runtime",
      start_ns: 0,
      end_ns: 100,
      status: "ok",
      attributes: {},
      events: [],
    },
    {
      id: "retrieval",
      parent_id: "root",
      name: "kb.retrieve",
      category: "retrieval",
      kind: "internal",
      service: "kb",
      start_ns: 100,
      end_ns: 300,
      status: "ok",
      attributes: {},
      events: [],
      input: { query: "refund" },
      normalized_payload: {
        chunks: [{ id: "policy#1", score: 0.9 }],
      },
      cost: {
        budget_source: "retrieval",
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        prompt_tokens: 0,
        tool_usd: 0.002,
        total_usd: 0.002,
      },
    },
    {
      id: "tool",
      parent_id: "root",
      name: "tool.lookup_order",
      category: "tool",
      kind: "client",
      service: "tool-host",
      start_ns: 300,
      end_ns: 600,
      status: "ok",
      attributes: { tool: "lookup_order" },
      events: [],
      input: { order_id: "ord_1" },
      output: { state: "open" },
      cost: {
        budget_source: "tool",
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        prompt_tokens: 0,
        tool_usd: 0.004,
        total_usd: 0.004,
      },
    },
  ],
};

describe("buildTraceScrubberModel", () => {
  it("derives ordered frames and cumulative cost from recorded spans", () => {
    const model = buildTraceScrubberModel(trace);

    expect(model.identity).toMatchObject({
      traceId: "trace_test",
      version: "v1",
      snapshotId: "snap_1",
    });
    expect(model.frames.map((frame) => frame.spanId)).toEqual([
      "root",
      "retrieval",
      "tool",
    ]);
    expect(model.frames[1]?.retrievalState).toContain("policy#1");
    expect(model.frames[2]?.nextToolCall).toContain("tool.lookup_order");
    expect(model.frames[2]?.costUsd).toBeCloseTo(0.006);
  });

  it("returns an explicit unsupported state for spanless traces", () => {
    const model = buildTraceScrubberModel({ id: "empty", spans: [] });

    expect(model.frames).toEqual([]);
    expect(model.unsupportedReason).toContain("no spans");
  });
});
