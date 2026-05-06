/**
 * UX403 — Marketplace and private skill library.
 *
 * Section 24.9 + 34 of the canonical target UX standard.
 *
 * Item kinds: tools, templates, skills, eval packs, KB connectors,
 * channel packs. Each item carries description, author, license,
 * version history, install count, rating, security posture, sample
 * evals, screenshots, required permissions, deprecation notice, and
 * trust metadata. Enterprise admins can curate allowed items and see
 * workspace usage. Private workspace publishing supports versioning,
 * deprecation, approvals/review, and usage analytics.
 */

export const MARKETPLACE_TRUST_LEVELS = [
  "verified",
  "internal",
  "community",
  "unverified",
] as const;

export type MarketplaceTrust = (typeof MARKETPLACE_TRUST_LEVELS)[number];

export const MARKETPLACE_TRUST_LABELS: Record<MarketplaceTrust, string> = {
  verified: "Verified",
  internal: "Internal",
  community: "Community",
  unverified: "Unverified",
};

export const MARKETPLACE_ITEM_KINDS = [
  "tool",
  "template",
  "skill",
  "eval-pack",
  "kb-connector",
  "channel-pack",
] as const;

export type MarketplaceItemKind = (typeof MARKETPLACE_ITEM_KINDS)[number];

export const MARKETPLACE_ITEM_KIND_LABELS: Record<MarketplaceItemKind, string> = {
  tool: "Tool",
  template: "Template",
  skill: "Skill",
  "eval-pack": "Eval pack",
  "kb-connector": "KB connector",
  "channel-pack": "Channel pack",
};

export const MARKETPLACE_PUBLISHERS = [
  "official",
  "verified-partner",
  "community",
  "private-workspace",
] as const;

export type MarketplacePublisher = (typeof MARKETPLACE_PUBLISHERS)[number];

export const MARKETPLACE_PERMISSIONS = [
  "read-traces",
  "write-tools",
  "external-network",
  "money-movement",
  "external-message",
  "read-pii",
  "write-secrets",
  "deploy-production",
] as const;

export type MarketplacePermission = (typeof MARKETPLACE_PERMISSIONS)[number];

export const MARKETPLACE_LIFECYCLE = [
  "draft",
  "in-review",
  "published",
  "deprecated",
  "archived",
] as const;

export type MarketplaceLifecycle = (typeof MARKETPLACE_LIFECYCLE)[number];

export interface MarketplaceVersion {
  version: string; // semver
  releasedAt: string; // ISO date
  changelog: string;
  signed: boolean;
  yanked?: boolean;
}

export interface MarketplaceSampleEval {
  id: string;
  name: string;
  passRate: number; // 0..1
  cases: number;
}

export interface MarketplaceItem {
  id: string;
  kind: MarketplaceItemKind;
  name: string;
  tagline: string;
  description: string;
  author: string;
  publisher: MarketplacePublisher;
  license: string;
  versions: MarketplaceVersion[]; // newest first
  installCount: number;
  rating: number; // 0..5
  ratingCount: number;
  trust: MarketplaceTrust;
  securityPosture: string;
  permissions: MarketplacePermission[];
  sampleEvals: MarketplaceSampleEval[];
  screenshots: string[]; // alt-text strings; renderer chooses placeholder
  lifecycle: MarketplaceLifecycle;
  deprecationNotice?: string;
  workspaceUsage7d?: number;
  reviewers?: string[];
}

/** Compute the current version from the (newest-first) version list. */
export function currentVersion(item: MarketplaceItem): MarketplaceVersion | null {
  const live = item.versions.find((v) => !v.yanked);
  return live ?? item.versions[0] ?? null;
}

/** Filter items by free-text query, kind, and publisher. */
export interface MarketplaceFilter {
  query?: string;
  kind?: MarketplaceItemKind | "all";
  publisher?: MarketplacePublisher | "all";
  curatedOnly?: boolean; // enterprise admin curation
  curatedIds?: ReadonlySet<string>;
  includeDeprecated?: boolean;
}

export function filterMarketplace(
  items: readonly MarketplaceItem[],
  filter: MarketplaceFilter,
): MarketplaceItem[] {
  const q = (filter.query ?? "").trim().toLowerCase();
  return items.filter((item) => {
    if (filter.kind && filter.kind !== "all" && item.kind !== filter.kind) return false;
    if (
      filter.publisher &&
      filter.publisher !== "all" &&
      item.publisher !== filter.publisher
    )
      return false;
    if (filter.curatedOnly) {
      if (!filter.curatedIds || !filter.curatedIds.has(item.id)) return false;
    }
    if (!filter.includeDeprecated && item.lifecycle === "deprecated") return false;
    if (item.lifecycle === "archived") return false;
    if (q) {
      const hay = [
        item.name,
        item.tagline,
        item.description,
        item.author,
        item.kind,
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

/** Submit a new private skill version for review. */
export interface PrivateSkillSubmission {
  itemId: string;
  version: string;
  changelog: string;
  permissions: MarketplacePermission[];
  reviewers: string[];
}

export interface SubmissionResult {
  ok: boolean;
  errors: string[];
  lifecycle: MarketplaceLifecycle;
}

/**
 * Validate a private skill submission. Submissions move to `in-review`
 * when at least one reviewer is named and a non-empty changelog is
 * provided. Money-movement, write-secrets, and deploy-production
 * require at least two reviewers.
 */
export function submitPrivateSkill(
  submission: PrivateSkillSubmission,
): SubmissionResult {
  const errors: string[] = [];
  if (!/^\d+\.\d+\.\d+$/.test(submission.version)) {
    errors.push("Version must be semver (major.minor.patch).");
  }
  if (submission.changelog.trim().length < 10) {
    errors.push("Changelog must explain what changed (10+ chars).");
  }
  if (submission.reviewers.length < 1) {
    errors.push("At least one reviewer is required.");
  }
  const sensitive: MarketplacePermission[] = [
    "money-movement",
    "write-secrets",
    "deploy-production",
  ];
  const usesSensitive = submission.permissions.some((p) => sensitive.includes(p));
  if (usesSensitive && submission.reviewers.length < 2) {
    errors.push("Sensitive permissions require two reviewers.");
  }
  return {
    ok: errors.length === 0,
    errors,
    lifecycle: errors.length === 0 ? "in-review" : "draft",
  };
}

/** Mark an item as deprecated with a notice. */
export function deprecateItem(
  item: MarketplaceItem,
  notice: string,
): MarketplaceItem {
  return { ...item, lifecycle: "deprecated", deprecationNotice: notice };
}

/** Default catalog used by the marketplace surface in fixture mode. */
export const DEFAULT_MARKETPLACE_CATALOG: readonly MarketplaceItem[] = [
  {
    id: "mk_tool_stripe_refund",
    kind: "tool",
    name: "Stripe refund",
    tagline: "Idempotent refunds with budget guardrails",
    description:
      "Issues full or partial refunds with a per-turn USD cap, evidence trail, and replay-safe idempotency keys.",
    author: "Loop Official",
    publisher: "official",
    license: "Apache-2.0",
    versions: [
      {
        version: "2.4.1",
        releasedAt: "2026-04-30",
        changelog: "Tighten idempotency window to 24h.",
        signed: true,
      },
      {
        version: "2.4.0",
        releasedAt: "2026-03-12",
        changelog: "Add partial-refund support.",
        signed: true,
      },
    ],
    installCount: 4128,
    rating: 4.7,
    ratingCount: 312,
    trust: "verified",
    securityPosture: "Signed, scoped to refunds.write, audited 2026-04",
    permissions: ["money-movement", "external-network"],
    sampleEvals: [
      { id: "ev_stripe_refund_basic", name: "Refund golden path", passRate: 1, cases: 24 },
      { id: "ev_stripe_refund_edges", name: "Edge: double refund", passRate: 0.95, cases: 20 },
    ],
    screenshots: ["Refund tool config", "Per-turn budget cap"],
    lifecycle: "published",
    workspaceUsage7d: 87,
  },
  {
    id: "mk_template_support_triage",
    kind: "template",
    name: "Support triage agent",
    tagline: "Refund-aware triage with HITL escalation",
    description:
      "Pre-wired behavior, tools, KB sources, and eval suite for a multilingual support triage agent.",
    author: "Loop Official",
    publisher: "official",
    license: "MIT",
    versions: [
      {
        version: "1.6.0",
        releasedAt: "2026-04-22",
        changelog: "Spanish refund coverage in eval suite.",
        signed: true,
      },
    ],
    installCount: 1932,
    rating: 4.6,
    ratingCount: 188,
    trust: "verified",
    securityPosture: "Signed template, no live tools wired by default",
    permissions: ["read-traces"],
    sampleEvals: [
      { id: "ev_triage_en", name: "English triage", passRate: 0.97, cases: 60 },
      { id: "ev_triage_es", name: "Spanish refund", passRate: 0.93, cases: 30 },
    ],
    screenshots: ["Behavior outline", "Eval suite preview"],
    lifecycle: "published",
    workspaceUsage7d: 12,
  },
  {
    id: "mk_skill_pii_redactor",
    kind: "skill",
    name: "PII redactor",
    tagline: "On-the-fly redaction for shared traces",
    description:
      "Reusable skill that masks emails, phones, secrets, and pricing before a trace is shared externally.",
    author: "Acme Internal Platform",
    publisher: "private-workspace",
    license: "Proprietary (workspace)",
    versions: [
      {
        version: "0.3.2",
        releasedAt: "2026-05-01",
        changelog: "Add Mexican phone format.",
        signed: false,
      },
    ],
    installCount: 18,
    rating: 4.4,
    ratingCount: 9,
    trust: "internal",
    securityPosture: "Workspace-private, reviewed by security@acme",
    permissions: ["read-pii"],
    sampleEvals: [
      { id: "ev_redactor", name: "Redaction precision", passRate: 0.99, cases: 50 },
    ],
    screenshots: ["Redaction preview"],
    lifecycle: "in-review",
    reviewers: ["sec-lead@acme", "ai-review@acme"],
    workspaceUsage7d: 4,
  },
  {
    id: "mk_eval_refund_regressions",
    kind: "eval-pack",
    name: "Refund regression pack",
    tagline: "30 cases covering refund edges across 4 locales",
    description:
      "Adversarial eval cases sourced from real escalations, anonymized and signed.",
    author: "Loop Official",
    publisher: "official",
    license: "Apache-2.0",
    versions: [
      {
        version: "1.2.0",
        releasedAt: "2026-04-18",
        changelog: "Add Portuguese refund variants.",
        signed: true,
      },
    ],
    installCount: 942,
    rating: 4.8,
    ratingCount: 64,
    trust: "verified",
    securityPosture: "Signed, no live data",
    permissions: ["read-traces"],
    sampleEvals: [
      { id: "ev_refund_pack", name: "All 30 cases", passRate: 0.9, cases: 30 },
    ],
    screenshots: ["Pack contents"],
    lifecycle: "published",
    workspaceUsage7d: 22,
  },
  {
    id: "mk_kb_zendesk",
    kind: "kb-connector",
    name: "Zendesk help center",
    tagline: "Sync articles with provenance",
    description:
      "Pulls articles, maintains chunk lineage, and surfaces freshness in the Atelier.",
    author: "Loop Official",
    publisher: "official",
    license: "Apache-2.0",
    versions: [
      {
        version: "3.0.0",
        releasedAt: "2026-04-04",
        changelog: "Provenance fields normalized.",
        signed: true,
      },
    ],
    installCount: 2210,
    rating: 4.5,
    ratingCount: 140,
    trust: "verified",
    securityPosture: "OAuth scoped to read:articles",
    permissions: ["external-network"],
    sampleEvals: [
      { id: "ev_zendesk_freshness", name: "Freshness probes", passRate: 0.96, cases: 12 },
    ],
    screenshots: ["Connector setup"],
    lifecycle: "published",
    workspaceUsage7d: 31,
  },
  {
    id: "mk_channel_whatsapp_business",
    kind: "channel-pack",
    name: "WhatsApp Business",
    tagline: "Templates, opt-in, session windows",
    description:
      "End-to-end channel pack with template registration and session-window enforcement.",
    author: "Verified Partner — Convo",
    publisher: "verified-partner",
    license: "Commercial",
    versions: [
      {
        version: "2.1.0",
        releasedAt: "2026-03-28",
        changelog: "Session-window enforcement.",
        signed: true,
      },
      {
        version: "2.0.0",
        releasedAt: "2026-01-12",
        changelog: "Major rewrite.",
        signed: true,
      },
    ],
    installCount: 612,
    rating: 4.3,
    ratingCount: 51,
    trust: "verified",
    securityPosture: "Signed, partner reviewed",
    permissions: ["external-message", "external-network"],
    sampleEvals: [
      { id: "ev_wa_templates", name: "Template approvals", passRate: 1, cases: 8 },
    ],
    screenshots: ["Channel config", "Template registration"],
    lifecycle: "published",
    workspaceUsage7d: 5,
  },
  {
    id: "mk_skill_legacy_translator",
    kind: "skill",
    name: "Legacy intent translator",
    tagline: "Translate legacy intent JSON to behavior sections",
    description:
      "Migration helper retained for parity audits. Replaced by the migration atelier importer.",
    author: "Loop Official",
    publisher: "official",
    license: "Apache-2.0",
    versions: [
      {
        version: "0.9.4",
        releasedAt: "2025-12-02",
        changelog: "Final maintenance release.",
        signed: true,
      },
    ],
    installCount: 142,
    rating: 3.9,
    ratingCount: 21,
    trust: "verified",
    securityPosture: "Read-only, no live tools",
    permissions: ["read-traces"],
    sampleEvals: [],
    screenshots: ["Translator preview"],
    lifecycle: "deprecated",
    deprecationNotice:
      "Replaced by the Botpress importer (Migration Atelier). Removal scheduled 2026-08.",
    workspaceUsage7d: 0,
  },
];

/** Format an install count with locale-friendly separators. */
export function formatInstallCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
  return String(n);
}
