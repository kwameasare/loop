import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BillingPanel } from "./billing-panel";
import {
  FIXTURE_BILLING,
  FIXTURE_BILLING_NOW_MS,
  PLANS,
  type BillingSummary,
} from "@/lib/billing";

function renderPanel(overrides: Partial<BillingSummary> = {}) {
  return render(
    <BillingPanel
      billing={{ ...FIXTURE_BILLING, ...overrides }}
      now_ms={FIXTURE_BILLING_NOW_MS}
    />,
  );
}

describe("BillingPanel", () => {
  it("renders the current plan, price, and change-plan CTA pointing to Stripe portal", () => {
    renderPanel();
    expect(screen.getByTestId("billing-plan-name").textContent).toBe(
      PLANS.growth.name,
    );
    expect(screen.getByTestId("billing-plan-price").textContent).toMatch(
      /\$199/,
    );
    const cta = screen.getByTestId("billing-change-plan");
    expect(cta).toHaveAttribute(
      "href",
      FIXTURE_BILLING.customer_portal_url,
    );
    expect(cta).toHaveAttribute("target", "_blank");
  });

  it("renders MTD usage bar and projection", () => {
    renderPanel();
    expect(screen.getByTestId("billing-usage-used").textContent).toMatch(
      /91,245/,
    );
    expect(screen.getByTestId("billing-usage-bar")).toBeInTheDocument();
    expect(
      screen.getByTestId("billing-usage-projection").textContent,
    ).toMatch(/msgs/);
  });

  it("flags overage when usage exceeds the included quota", () => {
    renderPanel({
      mtd_messages: 200_000,
      plan: PLANS.starter,
    });
    expect(screen.getByTestId("billing-usage-status").textContent).toMatch(
      /Over included quota/,
    );
  });

  it("shows empty payment state when no card is on file", () => {
    renderPanel({ payment_method_last4: null });
    expect(screen.getByTestId("billing-payment-empty")).toBeInTheDocument();
  });
});
