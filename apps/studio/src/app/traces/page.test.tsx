import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import TracesPage from "./page";

const navigationMocks = vi.hoisted(() => ({
  params: new URLSearchParams(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => navigationMocks.params,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_1", name: "Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("TracesPage", () => {
  afterEach(() => {
    navigationMocks.params = new URLSearchParams();
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("renders degraded trace evidence instead of a raw route error", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    const view = render(<TracesPage />);

    await waitFor(() => {
      expect(view.container).toHaveTextContent("Trace evidence is unavailable");
      expect(view.container).toHaveTextContent("LOOP_CP_API_BASE_URL");
    });
  });

  it("applies trace evidence query params instead of opening a generic list", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    navigationMocks.params = new URLSearchParams(
      "only_errors=true&agent_id=agent_support",
    );
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            workspace_id: "ws_1",
            trace_id: "trace_error",
            turn_id: "turn_1",
            conversation_id: "conv_1",
            agent_id: "agent_support",
            agent_name: "Support Agent",
            root_name: "turn",
            started_at: "2026-05-09T10:00:00Z",
            duration_ms: 100,
            span_count: 2,
            error: true,
          },
        ],
        next_cursor: null,
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    const view = render(<TracesPage />);

    await waitFor(() => {
      expect(view.getByTestId("trace-list-focused-query")).toHaveTextContent(
        "showing error traces",
      );
      expect(view.getByTestId("trace-filter-status")).toHaveValue("error");
      expect(view.getByTestId("trace-filter-agent")).toHaveValue(
        "agent_support",
      );
    });
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_1/traces?agent_id=agent_support&page_size=100",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
