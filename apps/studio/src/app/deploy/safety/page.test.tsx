import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import DeploySafetyPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_safety", name: "Safety Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("DeploySafetyPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("uses the selected what-could-break row as the live bisect target", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces/ws_safety/traces?page_size=8") {
        return Response.json({
          items: [
            {
              workspace_id: "ws_safety",
              trace_id: "trace_a_failure_001",
              turn_id: "turnaaaa1111",
              conversation_id: "conv_a",
              agent_id: "agent_a",
              started_at: "2026-05-10T12:00:00.000Z",
              duration_ms: 900,
              span_count: 4,
              error: true,
            },
            {
              workspace_id: "ws_safety",
              trace_id: "trace_b_failure_001",
              turn_id: "turnbbbb2222",
              conversation_id: "conv_b",
              agent_id: "agent_b",
              started_at: "2026-05-10T12:01:00.000Z",
              duration_ms: 1100,
              span_count: 5,
              error: true,
            },
          ],
          next_cursor: null,
        });
      }
      if (url === "https://cp.test/v1/audit/events?workspace_id=ws_safety&limit=20") {
        return Response.json({
          items: [
            {
              id: "audit_1",
              occurred_at: "2026-05-10T12:02:00.000Z",
              workspace_id: "ws_safety",
              actor_sub: "maya@example.com",
              action: "behavior.update",
              resource_type: "agent",
              resource_id: "agent_a",
              outcome: "success",
            },
          ],
          total: 1,
        });
      }
      if (url === "https://cp.test/v1/agents/agent_b/bisect") {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBe(
          JSON.stringify({
            failing_eval_case_id: "trace_b_failure_001",
            since_ref: "last-green",
            until_ref: "current",
          }),
        );
        return Response.json({
          status: "complete",
          failing_eval_case_id: "trace_b_failure_001",
          culprit: {
            ref: "v24",
            author: "sam@example.com",
            object: "behavior",
            confidence: 0.91,
            diff: "Changed escalation branch.",
          },
          elapsed_ms: 240,
        });
      }
      return Response.json({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<DeploySafetyPage />);

    expect(await screen.findByTestId("deploy-safety-page")).toBeInTheDocument();
    fireEvent.click(
      screen
        .getByTestId("wcb-row-live_bc_trace_b_fail")
        .querySelector("button")!,
    );
    fireEvent.click(screen.getByTestId("wcb-inspect-live_bc_trace_b_fail"));

    await waitFor(() => {
      expect(screen.getByTestId("bisect-case")).toHaveValue(
        "trace_b_failure_001",
      );
    });

    fireEvent.click(screen.getByTestId("bisect-run"));

    expect(await screen.findByText(/Regression bisect · trace_b_failure_001/i))
      .toBeInTheDocument();
    expect(screen.getByTestId("bisect-culprit")).toHaveTextContent("v24");
  });
});
