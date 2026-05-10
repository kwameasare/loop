import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentToolsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("AgentToolsPage", () => {
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("surfaces control-plane failures instead of pretending the catalog is simply empty", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(await AgentToolsPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("tools-room")).toBeInTheDocument();
    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required for tools calls/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("tools-room-import")).toBeInTheDocument();
  });

  it("surfaces a missing tool-binding route instead of an empty catalog", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () => new Response("missing", { status: 404 })),
    );

    render(await AgentToolsPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("tools-room")).toBeInTheDocument();
    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(screen.getByText(/tool-binding route/i)).toBeInTheDocument();
    expect(screen.queryByText("lookup_order")).not.toBeInTheDocument();
  });

  it("resolves tool contract evidence links to the owning tool", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.endsWith("/tools")) {
          return Response.json({
            items: [
              {
                id: "tool_issue_refund",
                name: "issue_refund",
                kind: "mcp",
                description: "Issue a refund.",
                source: "payments",
              },
            ],
          });
        }
        if (url.endsWith("/tool-contracts/metrics")) {
          return Response.json({
            items: [
              {
                tool_id: "tool_issue_refund",
                production_usage_7d: 2,
                success_rate_percent: 50,
                p95_latency_ms: 520,
                retry_rate_percent: 50,
                failed_calls_7d: 1,
                pii_sent_7d: 3,
                last_schema_change_at: "2026-05-10T00:00:00Z",
                measurement_status: "measured",
                evidence_ref: "tool-telemetry/tool_issue_refund/2-calls",
              },
            ],
          });
        }
        if (url.endsWith("/tool-contracts")) {
          return Response.json({
            items: [
              {
                id: "tc_refund",
                workspace_id: "ws",
                agent_id: "agent_support",
                tool_id: "tool_issue_refund",
                name: "issue_refund",
                description: "Issue a refund.",
                side_effect_level: "money_movement",
                pii_access: false,
                money_movement: true,
                rate_limits: {},
                budget_limits: {},
                sandbox_status: "sandbox",
                live_status: "review_required",
                owner_user_id: "owner@example.test",
                approval_policy_id: "policy-money",
                failure_behavior: "Escalate.",
                compensation_behavior: "Void pending refund.",
                content_hash: "hash_refund",
                approval_invalidated_at: null,
                created_at: "2026-05-09T00:00:00Z",
                updated_at: "2026-05-09T00:00:00Z",
              },
            ],
          });
        }
        return new Response("missing", { status: 404 });
      }),
    );

    render(
      await AgentToolsPage({
        params: { agent_id: "agent_support" },
        searchParams: { tool_contract_id: "tc_refund" },
      }),
    );

    expect(screen.getByTestId("tools-room-focused-tool")).toHaveTextContent(
      "issue_refund",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Production tool telemetry connected",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "tool-telemetry/tool_issue_refund/2-calls",
    );
  });
});
