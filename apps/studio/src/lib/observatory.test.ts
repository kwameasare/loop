import { describe, expect, it, vi } from "vitest";

import {
  buildObservatoryModel,
  fetchObservatoryModel,
  OBSERVATORY_MODEL,
} from "@/lib/observatory";
import type { InboxItem } from "@/lib/inbox";
import type { TraceSummary } from "@/lib/traces";
import type { UsageRecord } from "@/lib/costs";

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("buildObservatoryModel", () => {
  it("derives live quality, latency, cost, handoff, tail, and agent posture", () => {
    const traces: TraceSummary[] = [
      {
        id: "trace-ok",
        agent_id: "agent-a",
        agent_name: "Agent A",
        root_name: "turn ok",
        status: "ok",
        duration_ns: 900_000_000,
        started_at_ms: Date.UTC(2026, 4, 7, 12, 0, 0),
        span_count: 4,
      },
      {
        id: "trace-error",
        agent_id: "agent-a",
        agent_name: "Agent A",
        root_name: "turn error",
        status: "error",
        duration_ns: 2_500_000_000,
        started_at_ms: Date.UTC(2026, 4, 7, 12, 1, 0),
        span_count: 3,
      },
    ];
    const usage: UsageRecord[] = [
      {
        workspace_id: "ws1",
        agent_id: "agent-a",
        agent_name: "Agent A",
        metric: "tokens.in",
        quantity: 100,
        turn_count: 2,
        day_ms: Date.UTC(2026, 4, 7),
      },
      {
        workspace_id: "ws1",
        agent_id: "agent-a",
        agent_name: "Agent A",
        metric: "retrievals",
        quantity: 2,
        turn_count: 2,
        day_ms: Date.UTC(2026, 4, 7),
      },
    ];
    const inbox: InboxItem[] = [
      {
        id: "inbox-1",
        workspace_id: "ws1",
        team_id: "team",
        agent_id: "agent-a",
        channel: "web",
        conversation_id: "conv",
        user_id: "user",
        status: "pending",
        reason: "needs review",
        operator_id: null,
        created_at_ms: Date.UTC(2026, 4, 7, 12, 2, 0),
        claimed_at_ms: null,
        resolved_at_ms: null,
        last_message_excerpt: "help",
      },
    ];

    const model = buildObservatoryModel({
      workspaceId: "ws1",
      traces,
      usage,
      inbox,
      nowMs: Date.UTC(2026, 4, 7, 12, 3, 0),
    });

    expect(model.metrics.find((metric) => metric.id === "quality")?.value).toBe(
      "50.0%",
    );
    expect(model.metrics.find((metric) => metric.id === "latency")?.value).toBe(
      "2.50 s",
    );
    expect(model.anomalies.map((anomaly) => anomaly.id)).toContain(
      "live_trace_errors",
    );
    expect(model.tail[0]?.traceId).toBe("trace-error");
    expect(model.agents[0]).toMatchObject({
      id: "agent-a",
      evalPassRate: 50,
      tone: "blocked",
    });
  });
});

describe("fetchObservatoryModel", () => {
  it("falls back to the canonical fixture when cp-api is not configured", async () => {
    const model = await fetchObservatoryModel("ws1", { baseUrl: "" });
    expect(model).toBe(OBSERVATORY_MODEL);
  });

  it("loads traces, usage, and inbox from live cp-api routes", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/traces")) {
        return response({
          items: [
            {
              workspace_id: "ws1",
              trace_id: "trace-live",
              turn_id: "11111111-1111-1111-1111-111111111111",
              conversation_id: "22222222-2222-2222-2222-222222222222",
              agent_id: "agent-live",
              started_at: "2026-05-07T12:00:00Z",
              duration_ms: 700,
              span_count: 4,
              error: false,
            },
          ],
          next_cursor: null,
        });
      }
      if (url.includes("/usage")) {
        return response({
          items: [
            {
              workspace_id: "ws1",
              agent_id: "agent-live",
              agent_name: "Live Agent",
              metric: "tokens.out",
              quantity: 20,
              timestamp_ms: Date.UTC(2026, 4, 7, 12, 0, 0),
              turn_count: 1,
            },
          ],
        });
      }
      return response({ items: [] });
    });

    const model = await fetchObservatoryModel("ws1", {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(model.tail[0]?.traceId).toBe("trace-live");
    expect(model.agents[0]?.id).toBe("agent-live");
  });
});
