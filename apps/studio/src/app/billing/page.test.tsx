import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import BillingPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_billing", name: "Billing Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

function liveBillingSummary(): Record<string, unknown> {
  return {
    workspace_id: "ws_billing",
    plan: {
      id: "growth",
      name: "Growth",
      monthly_price_cents: 19900,
      included_messages: 150000,
      overage_per_message_cents: 1,
      features: ["90-day trace retention"],
    },
    cycle_start_ms: Date.UTC(2026, 4, 1),
    cycle_end_ms: Date.UTC(2026, 5, 1),
    mtd_messages: 12000,
    mtd_cost_cents: 19900,
    payment_method_last4: "4242",
    customer_portal_url: "https://billing.stripe.com/session",
  };
}

describe("BillingPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("does not claim billing is unprovisioned when billing summary route returns 404", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () => new Response("missing", { status: 404 })),
    );

    const view = render(<BillingPage />);

    await waitFor(() => {
      expect(view.container).toHaveTextContent("Billing evidence unavailable.");
    });
    expect(view.container).toHaveTextContent(
      "will not replace missing billing evidence with fixture spend",
    );
    expect(view.container).not.toHaveTextContent(
      "Billing is not yet provisioned",
    );
  });

  it("shows invoice degraded evidence when invoice route returns 404", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.endsWith("/billing"))
          return Response.json(liveBillingSummary());
        return new Response("missing", { status: 404 });
      }),
    );

    const view = render(<BillingPage />);

    await waitFor(() => {
      expect(view.getByTestId("invoice-list-degraded")).toHaveTextContent(
        "billing invoices route returned 404",
      );
    });
    expect(view.queryByTestId("invoice-empty")).not.toBeInTheDocument();
  });

  it("shows degraded billing evidence instead of a raw route alert when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(<BillingPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Billing evidence is degraded/i);
      expect(state).toHaveTextContent(/plan, usage, payment, or invoice/i);
      expect(state).toHaveTextContent(/LOOP_CP_API_BASE_URL is required/i);
    });
  });
});
