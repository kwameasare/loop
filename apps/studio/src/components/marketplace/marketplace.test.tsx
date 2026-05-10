import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketplaceDetail } from "@/components/marketplace/marketplace-detail";
import { MarketplaceGrid } from "@/components/marketplace/marketplace-grid";
import { MarketplaceOperations } from "@/components/marketplace/marketplace-operations";
import { PrivateSkillPublisher } from "@/components/marketplace/private-skill-publisher";
import {
  DEFAULT_MARKETPLACE_CATALOG,
  marketplaceItemFromCp,
} from "@/lib/marketplace";

describe("MarketplaceGrid", () => {
  function renderCatalog(
    props: Omit<ComponentProps<typeof MarketplaceGrid>, "items"> = {},
  ) {
    return render(
      <MarketplaceGrid items={DEFAULT_MARKETPLACE_CATALOG} {...props} />,
    );
  }

  it("renders an empty catalog without implicit fixture rows", () => {
    render(<MarketplaceGrid />);
    expect(screen.getByTestId("marketplace-empty")).toHaveTextContent(
      /no marketplace items/i,
    );
  });

  it("filters by free-text query", () => {
    renderCatalog();
    fireEvent.change(screen.getByTestId("marketplace-search"), {
      target: { value: "stripe" },
    });
    const list = screen.getByTestId("marketplace-list");
    expect(
      within(list).getByTestId("marketplace-card-mk_tool_stripe_refund"),
    ).toBeInTheDocument();
    expect(
      within(list).queryByTestId("marketplace-card-mk_kb_zendesk"),
    ).not.toBeInTheDocument();
  });

  it("shows empty state when nothing matches", () => {
    renderCatalog();
    fireEvent.change(screen.getByTestId("marketplace-search"), {
      target: { value: "nonexistent-xyz" },
    });
    expect(screen.getByTestId("marketplace-empty")).toHaveTextContent(
      /no marketplace items/i,
    );
  });

  it("respects enterprise curated allowlist", () => {
    renderCatalog({
      enterpriseCurated: true,
      curatedIds: new Set(["mk_template_support_triage"]),
    });
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
    renderCatalog({ onSelect });
    fireEvent.click(
      screen.getByTestId("marketplace-card-mk_tool_stripe_refund"),
    );
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0].id).toBe("mk_tool_stripe_refund");
  });

  it("hides deprecated items by default and shows them when opted in", () => {
    const { rerender } = render(
      <MarketplaceGrid items={DEFAULT_MARKETPLACE_CATALOG} />,
    );
    expect(
      screen.queryByTestId("marketplace-card-mk_skill_legacy_translator"),
    ).not.toBeInTheDocument();
    rerender(
      <MarketplaceGrid includeDeprecated items={DEFAULT_MARKETPLACE_CATALOG} />,
    );
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

describe("MarketplaceOperations", () => {
  const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_BASE === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE;
    vi.unstubAllGlobals();
  });

  it("loads install audit history and publishes private versions", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const item = DEFAULT_MARKETPLACE_CATALOG.find(
      (candidate) => candidate.id === "mk_skill_pii_redactor",
    )!;
    const onItemChanged = vi.fn();
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/installs?workspace_id=ws_marketplace")) {
        return Response.json({
          items: [
            {
              install_id: "inst_existing",
              item_id: item.id,
              workspace_id: "ws_marketplace",
              version: "0.3.2",
              installed_by: "owner-1",
              installed_at: "2026-05-09T12:00:00Z",
              audit_ref: "marketplace.install.mk_skill_pii_redactor",
            },
          ],
        });
      }
      if (url.endsWith("/versions") && init?.method === "POST") {
        return Response.json({
          server_id: item.id,
          slug: "skill-pii-redactor",
          name: item.name,
          publisher: "workspace:ws_marketplace",
          description: item.description,
          categories: ["private", "skill"],
          latest_version: "0.4.0",
          quality_score: 82,
          average_rating: 0,
          installs: 1,
          calls: 4,
          install_button_enabled: true,
          lifecycle: "published",
          permissions: ["read-pii"],
          versions: [
            {
              version: "0.4.0",
              released_at: "2026-05-09T12:01:00Z",
              changelog: "Adds passport redaction coverage.",
              signed: false,
            },
          ],
        });
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      <MarketplaceOperations
        item={item}
        workspaceId="ws_marketplace"
        onItemChanged={onItemChanged}
      />,
    );

    expect(await screen.findByTestId("marketplace-installs")).toHaveTextContent(
      "marketplace.install.mk_skill_pii_redactor",
    );
    fireEvent.change(screen.getByTestId("marketplace-version-input"), {
      target: { value: "0.4.0" },
    });
    fireEvent.change(screen.getByTestId("marketplace-version-changelog"), {
      target: { value: "Adds passport redaction coverage." },
    });
    fireEvent.click(screen.getByTestId("marketplace-publish-version"));

    expect(await screen.findByTestId("marketplace-operation-status")).toHaveTextContent(
      "Published version 0.4.0",
    );
    expect(onItemChanged).toHaveBeenCalledTimes(1);
    expect(onItemChanged.mock.calls[0]?.[0].versions[0]?.version).toBe("0.4.0");
  });

  it("adds the install result to audit history", async () => {
    const item = DEFAULT_MARKETPLACE_CATALOG.find(
      (candidate) => candidate.id === "mk_skill_pii_redactor",
    )!;

    render(
      <MarketplaceOperations
        item={item}
        installStatus={{
          installId: "inst_new",
          itemId: item.id,
          workspaceId: "ws_marketplace",
          version: "0.3.2",
          installedBy: "owner-1",
          installedAt: "2026-05-09T12:02:00Z",
          auditRef: "marketplace.install.mk_skill_pii_redactor",
        }}
      />,
    );

    expect(screen.getByTestId("marketplace-operation-status")).toHaveTextContent(
      "marketplace.install.mk_skill_pii_redactor",
    );
    expect(screen.getByTestId("marketplace-installs")).toHaveTextContent("v0.3.2");
  });
});

describe("marketplaceItemFromCp", () => {
  it("preserves private lifecycle, versions, permissions, and deprecation notice", () => {
    const item = marketplaceItemFromCp({
      server_id: "mk_private_refunds",
      slug: "private-refunds",
      name: "Private refunds",
      publisher: "workspace:ws_marketplace",
      description: "Internal refund helper",
      categories: ["private", "skill"],
      latest_version: "1.1.0",
      quality_score: 82,
      average_rating: 0,
      installs: 2,
      calls: 7,
      install_button_enabled: false,
      lifecycle: "deprecated",
      deprecation_notice: "Use refund skill v2.",
      permissions: ["money-movement"],
      versions: [
        {
          version: "1.1.0",
          released_at: "2026-05-09T12:00:00Z",
          changelog: "Adds stricter refund evidence.",
          signed: false,
        },
      ],
    });

    expect(item.kind).toBe("skill");
    expect(item.publisher).toBe("private-workspace");
    expect(item.lifecycle).toBe("deprecated");
    expect(item.deprecationNotice).toBe("Use refund skill v2.");
    expect(item.permissions).toContain("money-movement");
    expect(item.versions[0]).toMatchObject({
      version: "1.1.0",
      releasedAt: "2026-05-09",
    });
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
