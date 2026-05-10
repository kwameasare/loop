import { describe, expect, it, vi } from "vitest";

import { OBSERVATORY_MODEL } from "@/components/observatory/observatory-test-fixtures";
import {
  buildObservatoryModel,
  createObservatoryAnomalyEvalCase,
  createObservatoryAnomalyTask,
  fetchObservatoryModel,
  pinObservatoryMetric,
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
    expect(
      model.anomalies.find((anomaly) => anomaly.id === "live_trace_errors"),
    ).toMatchObject({
      affectedObject: "production trace cluster",
      traceQuery: "status:error",
    });
    expect(model.tail[0]?.traceId).toBe("trace-error");
    expect(model.agents[0]).toMatchObject({
      id: "agent-a",
      evalPassRate: 50,
      tone: "blocked",
    });
    expect(model.recommendation).toMatchObject({
      source: "observatory/anomaly/live_trace_errors",
      body:
        "Open the failed trace cluster and promote one failure into an eval case.",
      observed: "1 of 2 recent traces ended in error.",
    });
  });

  it("persists a metric as a custom dashboard layout", async () => {
    const fetcher = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        expect(String(input)).toBe(
          "https://cp.test/v1/workspaces/ws1/dashboards",
        );
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toMatchObject({
          name: "Quality watch",
          layout: [
            {
              source_type: "observatory_metric",
              source_id: "quality",
              title: "Quality",
            },
          ],
        });
        return response({
          id: "dash_1",
          name: "Pinned quality",
          layout: [{ metric_id: "quality" }],
        });
      },
    );

    const dashboard = await pinObservatoryMetric(
      "ws1",
      {
        id: "quality",
        label: "Quality",
        value: "98%",
        delta: "+2.0",
        tone: "healthy",
        nextAction: "Review the pinned quality traces.",
      },
      {
        baseUrl: "https://cp.test/v1",
        fetcher: fetcher as unknown as typeof fetch,
      },
    );

    expect(dashboard.id).toBe("dash_1");
  });

  it("creates tasks and eval cases from observatory anomalies through cp-api", async () => {
    const anomaly = OBSERVATORY_MODEL.anomalies[0]!;
    const fetcher = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const body = JSON.parse(String(init?.body));
        expect(body).toMatchObject({
          affected_object: anomaly.affectedObject,
          evidence: anomaly.evidence,
          trace_query: anomaly.traceQuery,
        });
        if (url.endsWith("/tasks")) {
          return response({
            id: "task_1",
            evidence: "task created from anomaly",
          });
        }
        return response({
          id: "eval_1",
          evidence: "eval created from anomaly",
        });
      },
    );

    const task = await createObservatoryAnomalyTask("ws1", anomaly, {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });
    const evalCase = await createObservatoryAnomalyEvalCase("ws1", anomaly, {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(task.id).toBe("task_1");
    expect(evalCase.id).toBe("eval_1");
    expect(fetcher).toHaveBeenCalledWith(
      `https://cp.test/v1/workspaces/ws1/observatory/anomalies/${anomaly.id}/tasks`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      `https://cp.test/v1/workspaces/ws1/observatory/anomalies/${anomaly.id}/eval-cases`,
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("fetchObservatoryModel", () => {
  it("returns an empty telemetry model when cp-api is not configured", async () => {
    const model = await fetchObservatoryModel("ws1", { baseUrl: "" });
    expect(model.degradedReason).toMatch(/LOOP_CP_API_BASE_URL/i);
    expect(model.agents).toEqual([]);
    expect(model.tail).toEqual([]);
    expect(model.metrics.every((metric) => metric.tone === "blocked")).toBe(
      true,
    );
    expect(model.anomalies[0]).toMatchObject({
      id: "telemetry_not_loaded",
      title: "No production telemetry loaded",
    });
    expect(model.recommendation).toMatchObject({
      source: "observatory/backend-required",
      confidenceLevel: "unsupported",
    });
  });

  it("loads traces, usage, inbox, and incidents from live cp-api routes", async () => {
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

    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(
      fetcher.mock.calls.some(([url]) => String(url).includes("/incidents")),
    ).toBe(true);
    expect(model.tail[0]?.traceId).toBe("trace-live");
    expect(model.agents[0]?.id).toBe("agent-live");
  });

  it("returns a degraded telemetry model when one live source fails", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/traces")) {
        return response({ message: "trace backend unavailable" }, 503);
      }
      return response({ items: [] });
    });

    const model = await fetchObservatoryModel("ws1", {
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(model.degradedReason).toMatch(
      /Live Observatory telemetry is unavailable/i,
    );
    expect(model.degradedReason).toMatch(/503/);
    expect(model.tail).toEqual([]);
    expect(model.agents).toEqual([]);
    expect(model.metrics.every((metric) => metric.tone === "blocked")).toBe(
      true,
    );
    expect(model.anomalies[0]?.id).toBe("telemetry_not_loaded");
  });
});
