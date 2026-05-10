import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import InboxPage from "./page";

const navigationMocks = vi.hoisted(() => ({
  params: new URLSearchParams(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => navigationMocks.params,
}));

vi.mock("@/lib/use-user", () => ({
  useUser: () => ({
    user: { sub: "operator_1", email: "operator@example.test" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_1", name: "Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("InboxPage", () => {
  afterEach(() => {
    navigationMocks.params = new URLSearchParams();
    if (ORIGINAL_BASE === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("renders degraded inbox state when the live HITL route is missing", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        new Response("missing", { status: 404 }),
      ),
    );

    const view = render(<InboxPage />);

    await waitFor(() => {
      expect(view.container).toHaveTextContent("operator inbox is unavailable");
      expect(view.container).toHaveTextContent("inbox route returned 404");
    });
    expect(view.container).not.toHaveTextContent("No pending handoffs");
  });

  it("honors agent evidence links instead of opening the generic inbox", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    navigationMocks.params = new URLSearchParams("agent_id=agent_billing");
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          items: [
            {
              id: "item_support",
              workspace_id: "ws_1",
              team_id: "team-care",
              agent_id: "agent_support",
              channel: "web",
              conversation_id: "conv_support",
              user_id: "support_user",
              status: "pending",
              reason: "support escalation",
              operator_id: null,
              created_at_ms: 1,
              claimed_at_ms: null,
              resolved_at_ms: null,
              last_message_excerpt: "support item",
            },
            {
              id: "item_billing",
              workspace_id: "ws_1",
              team_id: "team-billing",
              agent_id: "agent_billing",
              channel: "whatsapp",
              conversation_id: "conv_billing",
              user_id: "billing_user",
              status: "pending",
              reason: "billing escalation",
              operator_id: null,
              created_at_ms: 2,
              claimed_at_ms: null,
              resolved_at_ms: null,
              last_message_excerpt: "billing item",
            },
          ],
        }),
      ),
    );

    const view = render(<InboxPage />);

    await waitFor(() => {
      expect(view.getByTestId("inbox-focused-agent")).toHaveTextContent(
        "agent_billing",
      );
      expect(view.getByTestId("pending-row-item_billing")).toBeInTheDocument();
    });
    expect(view.queryByTestId("pending-row-item_support")).toBeNull();
  });
});
