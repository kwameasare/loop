import { describe, expect, it } from "vitest";

import {
  DEFAULT_MARKETPLACE_CATALOG,
  currentVersion,
  deprecateItem,
  fetchMarketplaceCatalog,
  filterMarketplace,
  formatInstallCount,
  marketplaceItemFromCp,
  submitPrivateSkill,
  type MarketplaceItem,
} from "./marketplace";

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("filterMarketplace", () => {
  it("matches by free-text query across name, tagline, and author", () => {
    const r = filterMarketplace(DEFAULT_MARKETPLACE_CATALOG, { query: "refund" });
    expect(r.map((i) => i.id)).toContain("mk_tool_stripe_refund");
    expect(r.map((i) => i.id)).toContain("mk_eval_refund_regressions");
  });

  it("filters by kind and publisher", () => {
    const r = filterMarketplace(DEFAULT_MARKETPLACE_CATALOG, {
      kind: "skill",
      publisher: "private-workspace",
    });
    expect(r.map((i) => i.id)).toEqual(["mk_skill_pii_redactor"]);
  });

  it("hides deprecated unless asked", () => {
    const without = filterMarketplace(DEFAULT_MARKETPLACE_CATALOG, {});
    expect(without.find((i) => i.id === "mk_skill_legacy_translator")).toBeUndefined();
    const withDep = filterMarketplace(DEFAULT_MARKETPLACE_CATALOG, {
      includeDeprecated: true,
    });
    expect(withDep.find((i) => i.id === "mk_skill_legacy_translator")).toBeDefined();
  });

  it("respects enterprise curation", () => {
    const curated = new Set(["mk_template_support_triage"]);
    const r = filterMarketplace(DEFAULT_MARKETPLACE_CATALOG, {
      curatedOnly: true,
      curatedIds: curated,
    });
    expect(r.map((i) => i.id)).toEqual(["mk_template_support_triage"]);
  });
});

describe("currentVersion", () => {
  it("returns the newest non-yanked version", () => {
    const item: MarketplaceItem = {
      ...DEFAULT_MARKETPLACE_CATALOG[0]!,
      versions: [
        { version: "3.0.0", releasedAt: "2026-05-01", changelog: "x", signed: true, yanked: true },
        { version: "2.4.1", releasedAt: "2026-04-30", changelog: "y", signed: true },
      ],
    };
    expect(currentVersion(item)?.version).toBe("2.4.1");
  });
});

describe("submitPrivateSkill", () => {
  it("requires semver, changelog, and at least one reviewer", () => {
    const r = submitPrivateSkill({
      itemId: "x",
      version: "1.0",
      changelog: "short",
      permissions: [],
      reviewers: [],
    });
    expect(r.ok).toBe(false);
    expect(r.lifecycle).toBe("draft");
    expect(r.errors).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/semver/i),
        expect.stringMatching(/changelog/i),
        expect.stringMatching(/reviewer/i),
      ]),
    );
  });

  it("requires two reviewers when sensitive permissions are requested", () => {
    const r = submitPrivateSkill({
      itemId: "x",
      version: "1.0.0",
      changelog: "Adds money-movement support to legacy connector.",
      permissions: ["money-movement"],
      reviewers: ["lead@a"],
    });
    expect(r.ok).toBe(false);
    expect(r.errors.some((e) => /two reviewers/i.test(e))).toBe(true);
  });

  it("moves to in-review on a clean submission", () => {
    const r = submitPrivateSkill({
      itemId: "x",
      version: "0.4.0",
      changelog: "Add Mexican phone redaction format.",
      permissions: ["read-pii"],
      reviewers: ["sec-lead@a"],
    });
    expect(r.ok).toBe(true);
    expect(r.lifecycle).toBe("in-review");
    expect(r.errors).toEqual([]);
  });
});

describe("deprecateItem", () => {
  it("marks lifecycle deprecated and stores notice", () => {
    const base = DEFAULT_MARKETPLACE_CATALOG[0]!;
    const out = deprecateItem(base, "Replaced by Stripe v3");
    expect(out.lifecycle).toBe("deprecated");
    expect(out.deprecationNotice).toBe("Replaced by Stripe v3");
    // immutability
    expect(base.lifecycle).toBe("published");
  });
});

describe("formatInstallCount", () => {
  it("formats large counts as compact 'k'", () => {
    expect(formatInstallCount(942)).toBe("942");
    expect(formatInstallCount(4128)).toBe("4.1k");
    expect(formatInstallCount(15000)).toBe("15k");
  });
});

describe("marketplace cp-api adapter", () => {
  it("maps first-party MCP browse items into Studio marketplace items", () => {
    const item = marketplaceItemFromCp({
      server_id: "first-party.salesforce",
      slug: "salesforce",
      name: "Salesforce",
      publisher: "loop",
      description: "Read Salesforce objects.",
      categories: ["crm", "read"],
      latest_version: "1.0.0",
      quality_score: 91,
      average_rating: 4.7,
      installs: 12,
      calls: 44,
      install_button_enabled: true,
    });

    expect(item).toMatchObject({
      id: "first-party.salesforce",
      kind: "tool",
      publisher: "official",
      trust: "verified",
      lifecycle: "published",
    });
    expect(item.permissions).toEqual(["external-network", "read-traces"]);
  });

  it("loads the live marketplace catalog when cp-api is configured", async () => {
    const fetcher = async (input: RequestInfo | URL) => {
      expect(String(input)).toBe("https://cp.test/v1/marketplace");
      return response({
        items: [
          {
            server_id: "first-party.salesforce",
            slug: "salesforce",
            name: "Salesforce",
            publisher: "loop",
            description: "Read Salesforce objects.",
            categories: ["crm", "read"],
            latest_version: "1.0.0",
            quality_score: 91,
            average_rating: 4.7,
            installs: 12,
            calls: 44,
            install_button_enabled: true,
          },
        ],
      });
    };

    const catalog = await fetchMarketplaceCatalog({
      baseUrl: "https://cp.test/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(catalog.map((item) => item.id)).toEqual(["first-party.salesforce"]);
  });
});
