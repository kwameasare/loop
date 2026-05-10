import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentEvalsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentEvalsPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded agent eval evidence instead of the old placeholder when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(await AgentEvalsPage({ params: { agent_id: "agent_eval" } }));

    expect(screen.getByTestId("agent-evals-page")).toBeInTheDocument();
    expect(screen.getByTestId("target-state")).toHaveAttribute(
      "data-state",
      "degraded",
    );
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /Agent evals is degraded/i,
    );
    expect(screen.getByTestId("target-state")).toHaveTextContent(
      /will not substitute fixture suites/i,
    );
    expect(screen.queryByTestId("agent-section-placeholder")).toBeNull();
  });

  it("shows only eval suites attached to the selected agent", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_eval")) {
        return Response.json({
          id: "agent_eval",
          name: "Eval Agent",
          description: "Evaluated support agent.",
          slug: "eval-agent",
          active_version: 3,
          created_at: "2026-05-09T10:00:00Z",
          workspace_id: "ws_eval",
        });
      }
      if (url === "https://cp.test/v1/workspaces/ws_eval/eval-suites") {
        return Response.json({
          items: [
            {
              id: "suite_agent",
              name: "Refund regression",
              agent_id: "agent_eval",
              cases: 12,
              last_run_at: "2026-05-09T10:05:00Z",
              pass_rate: 0.92,
            },
            {
              id: "suite_other",
              name: "Other agent suite",
              agent_id: "agent_other",
              cases: 4,
              last_run_at: null,
              pass_rate: null,
            },
          ],
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(await AgentEvalsPage({ params: { agent_id: "agent_eval" } }));

    expect(screen.getByTestId("eval-suites-list")).toBeInTheDocument();
    expect(screen.getByTestId("eval-suite-suite_agent")).toHaveTextContent(
      "Refund regression",
    );
    expect(screen.queryByTestId("eval-suite-suite_other")).toBeNull();
    expect(screen.queryByTestId("target-state")).toBeNull();
  });
});
