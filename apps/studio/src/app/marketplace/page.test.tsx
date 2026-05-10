import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import MarketplacePage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_marketplace", name: "Marketplace Workspace" },
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("MarketplacePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded catalog evidence instead of a local error panel when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(<MarketplacePage />);

    await waitFor(() => {
      expect(screen.getByTestId("target-state")).toHaveAttribute(
        "data-state",
        "degraded",
      );
    });
    expect(screen.getByText("Marketplace is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/catalog evidence could not load/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Select an item to see permissions/i),
    ).not.toBeInTheDocument();
  });

  it("installs the selected marketplace item through cp-api and surfaces audit evidence", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "https://cp.test/v1/marketplace") {
        return Response.json({
          items: [
            {
              server_id: "mk_private_refunds",
              slug: "private-refunds",
              name: "Private refunds",
              publisher: "workspace:ws_marketplace",
              description: "Internal refund helper",
              categories: ["private", "skill"],
              latest_version: "1.0.0",
              quality_score: 82,
              average_rating: 0,
              installs: 0,
              calls: 7,
              install_button_enabled: true,
              lifecycle: "published",
              permissions: ["money-movement"],
              versions: [
                {
                  version: "1.0.0",
                  released_at: "2026-05-09T12:00:00Z",
                  changelog: "Initial release.",
                  signed: false,
                },
              ],
            },
          ],
        });
      }
      if (url.endsWith("/items/mk_private_refunds/installs?workspace_id=ws_marketplace")) {
        return Response.json({ items: [] });
      }
      if (
        url.endsWith("/items/mk_private_refunds/install") &&
        init?.method === "POST"
      ) {
        return Response.json(
          {
            install_id: "inst_private_refunds",
            item_id: "mk_private_refunds",
            workspace_id: "ws_marketplace",
            version: "1.0.0",
            installed_by: "owner-1",
            installed_at: "2026-05-09T12:05:00Z",
            audit_ref: "marketplace.install.mk_private_refunds",
          },
          { status: 201 },
        );
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<MarketplacePage />);

    expect(await screen.findByTestId("marketplace-detail-mk_private_refunds")).toHaveTextContent(
      "Private refunds",
    );
    fireEvent.click(screen.getByTestId("marketplace-install-mk_private_refunds"));

    expect(await screen.findByTestId("marketplace-operation-status")).toHaveTextContent(
      "marketplace.install.mk_private_refunds",
    );
    expect(screen.getByTestId("marketplace-installs")).toHaveTextContent("v1.0.0");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/marketplace/items/mk_private_refunds/install",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ workspace_id: "ws_marketplace" }),
      }),
    );
  });
});
