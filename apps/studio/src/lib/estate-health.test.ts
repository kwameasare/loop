import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  deriveEstateHealthFromAgents,
  fetchEstateHealth,
  type EstateHealth,
} from "@/lib/estate-health";
import type { AgentSummary } from "@/lib/cp-api";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_TOKEN = process.env.LOOP_TOKEN;

const AGENTS: AgentSummary[] = [
  {
    id: "agt_draft",
    name: "Draft agent",
    description: "Needs gates.",
    slug: "draft-agent",
    active_version: null,
    updated_at: "2026-05-08T12:00:00Z",
    workspace_id: "ws_1",
  },
  {
    id: "agt_prod",
    name: "Production agent",
    description: "",
    slug: "production-agent",
    active_version: 3,
    updated_at: "2026-05-08T13:00:00Z",
    workspace_id: "ws_1",
  },
];

describe("estate health", () => {
  beforeEach(() => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.LOOP_TOKEN;
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    process.env.LOOP_TOKEN = ORIGINAL_TOKEN;
    vi.restoreAllMocks();
  });

  it("derives an honest fallback from real agent rows", () => {
    const health = deriveEstateHealthFromAgents(AGENTS, {
      workspaceId: "ws_1",
      dataSource: "derived",
    });

    expect(health.summary.agents_total).toBe(2);
    expect(health.summary.agents_draft).toBe(1);
    expect(health.summary.agents_production).toBe(1);
    expect(health.attention[0]).toMatchObject({
      id: "draft-agent-agt_draft",
      source: "agents/agt_draft.active_version",
    });
  });

  it("does not invent liveness when cp-api is unconfigured", async () => {
    const health = await fetchEstateHealth("ws_1", { fallbackAgents: AGENTS });

    expect(health.data_source).toBe("unconfigured");
    expect(health.degraded_reason).toMatch(/LOOP_CP_API_BASE_URL/);
    expect(health.summary.agents_total).toBe(2);
  });

  it("loads estate health from cp-api when configured", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    process.env.LOOP_TOKEN = "test-token";
    const body: EstateHealth = {
      workspace_id: "ws_1",
      generated_at: "2026-05-08T12:00:00Z",
      data_source: "live",
      provenance: ["agents.list_for_workspace"],
      summary: {
        agents_total: 4,
        agents_production: 3,
        agents_draft: 1,
        pending_handoffs: 2,
        pending_approvals: 1,
        trace_errors: 1,
        trace_count: 44,
        eval_suites: 5,
        audit_events: 9,
        open_incidents: 0,
        blocked_deploys: 1,
      },
      attention: [],
      shared_dependencies: [
        {
          id: "tool:refund_payment",
          type: "tool",
          name: "refund_payment",
          agents: [
            {
              agent_id: "agt_1",
              agent_name: "Refund Agent",
              evidence_ref: "tool-contract/tc_1",
            },
          ],
          risk: "high",
          detail: "Shared money-moving tool.",
          evidence_ref: "tool-contract/tc_1",
        },
      ],
      channel_health: [],
      failure_clusters: [],
      background_jobs: [
        {
          id: "cluster_failures",
          status: "completed",
          output_count: 0,
          evidence_ref: "estate/jobs/cluster_failures",
        },
      ],
      next_actions: [],
    };
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => body,
    });

    const health = await fetchEstateHealth("ws_1", { fetcher });

    expect(health).toBe(body);
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_1/estate-health",
      expect.objectContaining({
        cache: "no-store",
        headers: expect.objectContaining({
          authorization: "Bearer test-token",
        }),
        method: "GET",
      }),
    );
  });

  it("falls back with an explicit unavailable source on non-2xx", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({}),
    });

    const health = await fetchEstateHealth("ws_1", {
      fetcher,
      fallbackAgents: AGENTS,
    });

    expect(health.data_source).toBe("unavailable");
    expect(health.degraded_reason).toContain("503");
    expect(health.summary.agents_total).toBe(2);
  });
});
