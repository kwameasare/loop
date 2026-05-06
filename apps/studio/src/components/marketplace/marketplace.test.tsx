import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarketplaceDetail } from "@/components/marketplace/marketplace-detail";
import { MarketplaceGrid } from "@/components/marketplace/marketplace-grid";
import { PrivateSkillPublisher } from "@/components/marketplace/private-skill-publisher";
import { DEFAULT_MARKETPLACE_CATALOG } from "@/lib/marketplace";

describe("MarketplaceGrid", () => {
  it("filters by free-text query", () => {
    render(<MarketplaceGrid />);
    fireEvent.change(screen.getByTestId("marketplace-search"), {
      target: { value: "stripe" },
    });
    const list = screen.getByTestId("marketplace-list");
    expect(within(list).getByTestId("marketplace-card-mk_tool_stripe_refund")).toBeInTheDocument();
    expect(
      within(list).queryByTestId("marketplace-card-mk_kb_zendesk"),
    ).not.toBeInTheDocument();
  });

  it("shows empty state when nothing matches", () => {
    render(<MarketplaceGrid />);
    fireEvent.change(screen.getByTestId("marketplace-search"), {
      target: { value: "nonexistent-xyz" },
    });
    expect(screen.getByTestId("marketplace-empty")).toHaveTextContent(/no marketplace items/i);
  });

  it("respects enterprise curated allowlist", () => {
    render(
      <MarketplaceGrid
        enterpriseCurated
        curatedIds={new Set(["mk_template_support_triage"])}
      />,
    );
    expect(screen.getByTestId("marketplace-curated-badge")).toBeInTheDocument();
    expect(
      screen.getByTestId("marketplace-card-mk_template_support_triage"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("marketplace-card-mk_tool_stripe_refund"),
    ).not.toBeInTheDocument();
  });

  it("invokes onSelect with the picked item", () => {
    const onSelect = vi.fn();
    render(<MarketplaceGrid onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("marketplace-card-mk_tool_stripe_refund"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0].id).toBe("mk_tool_stripe_refund");
  });

  it("hides deprecated items by default and shows them when opted in", () => {
    const { rerender } = render(<MarketplaceGrid />);
    expect(
      screen.queryByTestId("marketplace-card-mk_skill_legacy_translator"),
    ).not.toBeInTheDocument();
    rerender(<MarketplaceGrid includeDeprecated />);
    expect(
      screen.getByTestId("marketplace-card-mk_skill_legacy_translator"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("marketplace-card-deprecation-mk_skill_legacy_translator"),
    ).toHaveTextContent(/replaced/i);
  });
});

describe("MarketplaceDetail", () => {
  it("renders permissions, security posture, sample evals, screenshots, and version history", () => {
    const item = DEFAULT_MARKETPLACE_CATALOG.find((i) => i.id === "mk_tool_stripe_refund")!;
    render(<MarketplaceDetail item={item} />);
    const perms = screen.getByTestId("marketplace-detail-permissions");
    expect(within(perms).getByText("money-movement")).toBeInTheDocument();
    expect(screen.getByTestId("marketplace-detail-evals")).toHaveTextContent(/refund/i);
    expect(screen.getByTestId("marketplace-detail-screenshots")).toBeInTheDocument();
    const versions = screen.getByTestId("marketplace-detail-versions");
    expect(within(versions).getByText(/2\.4\.1/)).toBeInTheDocument();
    expect(within(versions).getByText(/current/i)).toBeInTheDocument();
  });

  it("disables Install for deprecated items and surfaces the notice", () => {
    const item = DEFAULT_MARKETPLACE_CATALOG.find(
      (i) => i.id === "mk_skill_legacy_translator",
    )!;
    render(<MarketplaceDetail item={item} />);
    const btn = screen.getByTestId(`marketplace-install-${item.id}`);
    expect(btn).toBeDisabled();
    expect(screen.getByTestId("marketplace-detail-deprecation")).toHaveTextContent(
      /replaced/i,
    );
  });

  it("calls onInstall for published items", () => {
    const item = DEFAULT_MARKETPLACE_CATALOG.find((i) => i.id === "mk_tool_stripe_refund")!;
    const onInstall = vi.fn();
    render(<MarketplaceDetail item={item} onInstall={onInstall} />);
    fireEvent.click(screen.getByTestId(`marketplace-install-${item.id}`));
    expect(onInstall).toHaveBeenCalledWith(item);
  });
});

describe("PrivateSkillPublisher", () => {
  it("rejects an incomplete submission and lists the errors", () => {
    const onSubmit = vi.fn();
    render(<PrivateSkillPublisher itemId="mk_skill_pii_redactor" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByTestId("publisher-submit"));
    const result = screen.getByTestId("publisher-result");
    expect(result).toHaveTextContent(/changelog/i);
    expect(result).toHaveTextContent(/reviewer/i);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0]?.[0].ok).toBe(false);
  });

  it("requires two reviewers when sensitive permissions are checked", () => {
    render(<PrivateSkillPublisher itemId="mk_skill_demo" />);
    fireEvent.change(screen.getByTestId("publisher-version"), {
      target: { value: "1.0.0" },
    });
    fireEvent.change(screen.getByTestId("publisher-changelog"), {
      target: { value: "Add money-movement support to the legacy connector." },
    });
    fireEvent.click(screen.getByTestId("publisher-permission-money-movement"));
    fireEvent.change(screen.getByTestId("publisher-reviewers"), {
      target: { value: "lead@a" },
    });
    fireEvent.click(screen.getByTestId("publisher-submit"));
    expect(screen.getByTestId("publisher-result")).toHaveTextContent(
      /two reviewers/i,
    );
  });

  it("accepts a clean submission and reports in-review lifecycle", () => {
    const onSubmit = vi.fn();
    render(<PrivateSkillPublisher itemId="mk_skill_demo" onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("publisher-version"), {
      target: { value: "0.4.0" },
    });
    fireEvent.change(screen.getByTestId("publisher-changelog"), {
      target: { value: "Adds Mexican phone format to redactor." },
    });
    fireEvent.click(screen.getByTestId("publisher-permission-read-pii"));
    fireEvent.change(screen.getByTestId("publisher-reviewers"), {
      target: { value: "sec@a" },
    });
    fireEvent.click(screen.getByTestId("publisher-submit"));
    expect(screen.getByTestId("publisher-result")).toHaveTextContent(/in-review/);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0]?.[0].lifecycle).toBe("in-review");
  });
});
