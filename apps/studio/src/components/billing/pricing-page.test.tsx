import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  PricingPage,
  type PricingFeature,
  type PricingPlan,
} from "./pricing-page";

const FEATURES: PricingFeature[] = [
  { id: "agents", label: "Agents", description: "Per workspace" },
  { id: "evals", label: "Eval runs / mo" },
  { id: "sso", label: "SSO (SAML/OIDC)" },
  { id: "audit", label: "Audit-log export" },
  { id: "byo_vault", label: "BYO Vault" },
];

const PLANS: PricingPlan[] = [
  {
    id: "starter",
    name: "Starter",
    price_cents: 0,
    tagline: "For tinkerers and side projects.",
    highlights: ["1 workspace", "Community support", "1k traces / mo"],
    matrix: { agents: "3", evals: "100", sso: "no", audit: "no", byo_vault: "no" },
    cta_href: "/signup?plan=starter",
  },
  {
    id: "team",
    name: "Team",
    price_cents: 4900,
    tagline: "For shipping teams.",
    recommended: true,
    highlights: ["Unlimited agents", "Email support", "100k traces / mo"],
    matrix: {
      agents: "Unlimited",
      evals: "10,000",
      sso: "limited",
      audit: "yes",
      byo_vault: "no",
    },
    cta_href: "/signup?plan=team",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price_cents: null,
    tagline: "For regulated industries.",
    highlights: ["SSO + SCIM", "BYO Vault", "Dedicated SE"],
    matrix: {
      agents: "Unlimited",
      evals: "Unlimited",
      sso: "yes",
      audit: "yes",
      byo_vault: "yes",
    },
    cta_label: "Talk to sales",
    cta_href: "/contact",
  },
];

describe("PricingPage (S671)", () => {
  it("renders all three plan cards with prices", () => {
    render(<PricingPage plans={PLANS} features={FEATURES} variant="A" />);
    expect(screen.getByTestId("plan-card-starter")).toHaveTextContent("Free");
    expect(screen.getByTestId("plan-card-team")).toHaveTextContent("$49");
    expect(screen.getByTestId("plan-card-team")).toHaveTextContent("/mo");
    expect(screen.getByTestId("plan-card-enterprise")).toHaveTextContent(
      "Talk to sales",
    );
  });

  it("highlights the recommended plan with the popular badge", () => {
    render(<PricingPage plans={PLANS} features={FEATURES} variant="A" />);
    const team = screen.getByTestId("plan-card-team");
    expect(team).toHaveAttribute("aria-label", "Team plan");
    expect(team).toHaveTextContent("Most popular");
  });

  it("renders a row in the comparison matrix for every feature", () => {
    render(<PricingPage plans={PLANS} features={FEATURES} variant="A" />);
    for (const f of FEATURES) {
      expect(screen.getByTestId(`matrix-row-${f.id}`)).toBeInTheDocument();
    }
  });

  it("uses semantic accessibility markers on yes/no/limited cells", () => {
    render(<PricingPage plans={PLANS} features={FEATURES} variant="A" />);
    expect(screen.getAllByLabelText("included").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("not included").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("limited").length).toBeGreaterThan(0);
  });

  it("varies headline copy by A/B variant and exposes data-variant", () => {
    const { rerender } = render(
      <PricingPage plans={PLANS} features={FEATURES} variant="A" />,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Simple pricing for every team",
    );
    expect(screen.getByTestId("pricing-page")).toHaveAttribute(
      "data-variant",
      "A",
    );
    rerender(<PricingPage plans={PLANS} features={FEATURES} variant="B" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Pick the plan that scales with you",
    );
    expect(screen.getByTestId("pricing-page")).toHaveAttribute(
      "data-variant",
      "B",
    );
  });

  it("invokes onCtaClick with plan id and variant", () => {
    const onCta = vi.fn();
    render(
      <PricingPage
        plans={PLANS}
        features={FEATURES}
        variant="B"
        onCtaClick={onCta}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /talk to sales/i }));
    expect(onCta).toHaveBeenCalledWith("enterprise", "B");
  });

  it("uses scoped table headers for screen readers", () => {
    render(<PricingPage plans={PLANS} features={FEATURES} variant="A" />);
    const table = screen.getByTestId("plan-comparison-matrix");
    const colHeaders = table.querySelectorAll('th[scope="col"]');
    expect(colHeaders.length).toBe(1 + PLANS.length);
    const rowHeaders = table.querySelectorAll('th[scope="row"]');
    expect(rowHeaders.length).toBe(FEATURES.length);
  });
});
