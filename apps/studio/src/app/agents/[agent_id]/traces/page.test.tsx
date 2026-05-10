import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentTracesPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentTracesPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded agent trace evidence instead of the old placeholder when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(await AgentTracesPage({ params: { agent_id: "agent_trace" } }));

    expect(screen.getByTestId("agent-traces-page")).toBeInTheDocument();
    expect(screen.getByTestId("target-state")).toHaveAttribute(
      "data-state",
      "degraded",
    );
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /Agent traces is degraded/i,
    );
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /will not substitute fixture turns/i,
    );
    expect(screen.queryByTestId("agent-section-placeholder")).toBeNull();
  });

  it("loads trace rows scoped to the selected agent workspace", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_trace")) {
        return Response.json({
          id: "agent_trace",
          name: "Trace Agent",
          description: "Traceable support agent.",
          slug: "trace-agent",
          active_version: 8,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_trace",
        });
      }
      if (
        url ===
        "https://cp.test/v1/workspaces/ws_trace/traces?agent_id=agent_trace&page_size=100"
      ) {
        return Response.json({
          items: [
            {
              workspace_id: "ws_trace",
              trace_id: "trc_agent_001",
              turn_id: "turn_agent_001",
              conversation_id: "cnv_agent_001",
              agent_id: "agent_trace",
              started_at: "2026-05-09T10:05:00Z",
              duration_ms: 840,
              span_count: 6,
              error: false,
            },
          ],
          next_cursor: null,
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(await AgentTracesPage({ params: { agent_id: "agent_trace" } }));

    expect(screen.getByTestId("trace-list")).toBeInTheDocument();
    expect(screen.getByTestId("trace-row-trc_agent_001")).toHaveTextContent(
      "trc_agent_001",
    );
    expect(screen.getByTestId("trace-row-trc_agent_001")).toHaveTextContent(
      "agent_trace",
    );
    expect(screen.queryByTestId("target-state")).toBeNull();
  });

  it("applies Workbench trace filter params to the visible trace list", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_trace")) {
        return Response.json({
          id: "agent_trace",
          name: "Trace Agent",
          description: "Traceable support agent.",
          slug: "trace-agent",
          active_version: 8,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_trace",
        });
      }
      if (
        url ===
        "https://cp.test/v1/workspaces/ws_trace/traces?agent_id=agent_trace&page_size=100"
      ) {
        return Response.json({
          items: [
            {
              workspace_id: "ws_trace",
              trace_id: "trc_agent_error",
              turn_id: "turn_agent_error",
              conversation_id: "cnv_agent_error",
              agent_id: "agent_trace",
              root_name: "tool.lookup",
              started_at: "2026-05-09T10:05:00Z",
              duration_ms: 840,
              span_count: 6,
              error: true,
            },
          ],
          next_cursor: null,
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await AgentTracesPage({
        params: { agent_id: "agent_trace" },
        searchParams: { filter: "failed", span: "tool" },
      }),
    );

    expect(screen.getByTestId("trace-list-focused-query")).toHaveTextContent(
      "filtering traces by tool spans",
    );
    expect(screen.getByTestId("trace-filter-status")).toHaveValue("error");
    expect(screen.getByTestId("trace-search")).toHaveValue("tool");
  });
});
