import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentObservabilityPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentObservabilityPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded observability evidence instead of the old placeholder when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      await AgentObservabilityPage({ params: { agent_id: "agent_observe" } }),
    );

    expect(screen.getByTestId("agent-observability-page")).toBeInTheDocument();
    expect(screen.getByTestId("observatory-screen")).toBeInTheDocument();
    expect(screen.getByTestId("observatory-degraded")).toHaveTextContent(
      /Live agent data is unavailable/i,
    );
    expect(screen.queryByTestId("agent-section-placeholder")).toBeNull();
  });

  it("builds observability from agent-scoped traces, usage, handoffs, and incidents", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_observe")) {
        return Response.json({
          id: "agent_observe",
          name: "Observe Agent",
          description: "Observed support agent.",
          slug: "observe-agent",
          active_version: 4,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_observe",
        });
      }
      if (
        url ===
        "https://cp.test/v1/workspaces/ws_observe/traces?agent_id=agent_observe&page_size=100"
      ) {
        return Response.json({
          items: [
            {
              workspace_id: "ws_observe",
              trace_id: "trc_observe_001",
              turn_id: "turn_observe_001",
              conversation_id: "cnv_observe_001",
              agent_id: "agent_observe",
              started_at: "2026-05-09T10:05:00Z",
              duration_ms: 940,
              span_count: 6,
              error: false,
            },
          ],
          next_cursor: null,
        });
      }
      if (url.startsWith("https://cp.test/v1/workspaces/ws_observe/usage?")) {
        return Response.json({
          items: [
            {
              workspace_id: "ws_observe",
              agent_id: "agent_observe",
              agent_name: "Observe Agent",
              metric: "tokens.in",
              quantity: 1200,
              timestamp_ms: Date.UTC(2026, 4, 9),
              turn_count: 12,
            },
          ],
        });
      }
      if (url === "https://cp.test/v1/workspaces/ws_observe/inbox") {
        return Response.json({ items: [] });
      }
      if (url === "https://cp.test/v1/agents/agent_observe/incidents") {
        return Response.json({ items: [] });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await AgentObservabilityPage({ params: { agent_id: "agent_observe" } }),
    );

    expect(screen.getByTestId("observatory-screen")).toBeInTheDocument();
    expect(
      screen.getByTestId("ambient-health-agent_observe"),
    ).toHaveTextContent("agent_observe");
    expect(screen.queryByTestId("observatory-degraded")).toBeNull();
  });

  it("focuses incident response from Workbench evidence links", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_observe")) {
        return Response.json({
          id: "agent_observe",
          name: "Observe Agent",
          description: "Observed support agent.",
          slug: "observe-agent",
          active_version: 4,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_observe",
        });
      }
      if (
        url ===
        "https://cp.test/v1/workspaces/ws_observe/traces?agent_id=agent_observe&page_size=100"
      ) {
        return Response.json({ items: [], next_cursor: null });
      }
      if (url.startsWith("https://cp.test/v1/workspaces/ws_observe/usage?")) {
        return Response.json({ items: [] });
      }
      if (url === "https://cp.test/v1/workspaces/ws_observe/inbox") {
        return Response.json({ items: [] });
      }
      if (url === "https://cp.test/v1/agents/agent_observe/incidents") {
        return Response.json({
          items: [
            {
              id: "inc_1",
              workspace_id: "ws_observe",
              agent_id: "agent_observe",
              severity: "high",
              status: "contained",
              trigger: "Refund route drift",
              affected_trace_ids: ["trc_1"],
              affected_conversation_count: 1,
              rollback_action_ref: "rollback_1",
              root_cause_hypothesis: "Policy synonym drift.",
              proposed_fix: "Patch refund synonym behavior.",
              candidate_eval_suite_id: null,
              fix_change_package_id: null,
              notifications: [],
              created_at: "2026-05-09T10:00:00Z",
              updated_at: "2026-05-09T10:00:00Z",
            },
          ],
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await AgentObservabilityPage({
        params: { agent_id: "agent_observe" },
        searchParams: { view: "incidents" },
      }),
    );

    expect(
      screen.getByTestId("observatory-focused-incidents"),
    ).toHaveTextContent("Opened from Workbench evidence");
    expect(screen.getByTestId("observatory-incidents")).toHaveClass(
      "ring-focus",
    );
  });
});
