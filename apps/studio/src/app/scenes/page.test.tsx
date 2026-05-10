import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import ScenesPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_1", name: "Workspace", slug: "workspace", role: "owner" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("ScenesPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders degraded evidence instead of a demo scene library without cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(<ScenesPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /scenes is degraded/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/will not substitute a demo scene library/i))
        .toBeInTheDocument();
      expect(screen.getByText(/LOOP_CP_API_BASE_URL/i)).toBeInTheDocument();
    });
  });

  it("lists workspace scenes and queues replay through cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces/ws_1/scenes") {
        return Response.json({
          items: [
            {
              id: "scene_refund",
              name: "Refund escalation",
              category: "refund",
              trace_ids: ["trace_1", "trace_2"],
              expected_behavior: "Escalate legal threats after policy citation.",
              created_by: "maya@example.com",
              created_at: "2026-05-10T12:00:00.000Z",
            },
          ],
        });
      }
      if (
        url === "https://cp.test/v1/workspaces/ws_1/scenes/scene_refund/replay"
      ) {
        expect(init?.method).toBe("POST");
        return Response.json({
          scene_id: "scene_refund",
          status: "queued",
          trace_ids: ["trace_1", "trace_2"],
          draft_replay_id: "rpl_scene_1",
        });
      }
      return Response.json({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ScenesPage />);

    expect(await screen.findByText("Refund escalation")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("scene-replay-button-scene_refund"));

    expect(await screen.findByTestId("scene-replay-scene_refund"))
      .toHaveTextContent("rpl_scene_1");
  });
});
