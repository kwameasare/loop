import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import InboxPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
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
});
