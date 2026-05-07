/**
 * Sharing, redaction, access log, revoke, and quick-branch links.
 *
 * Implements sections 27.4, 27.5, and 27.7 of the canonical UX standard. The
 * helpers stay pure so the share dialog and quick-branch-link components can
 * preview redactions and generate URLs without any browser-only dependency.
 */

import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

/** Artifacts the canonical standard allows sharing (section 27.4). */
export const SHAREABLE_ARTIFACTS = [
  "trace",
  "conversation",
  "eval-result",
  "deploy-diff",
  "parity-report",
  "cost-chart",
  "audit-evidence",
  "branch",
] as const;

export type ShareArtifact = (typeof SHAREABLE_ARTIFACTS)[number];

/** Canonical sharing scopes (section 27.4). */
export const SHARE_SCOPES = [
  "workspace",
  "named-people",
  "link-anyone",
  "branch-reviewers",
] as const;

export type ShareScope = (typeof SHARE_SCOPES)[number];

/** Redaction categories that the recipient is told about (section 27.5). */
export const REDACTION_CATEGORIES = [
  "pii",
  "secrets",
  "customer-messages",
  "prompts",
  "pricing",
  "internal-notes",
] as const;

export type RedactionCategory = (typeof REDACTION_CATEGORIES)[number];

export interface RedactionPolicy {
  categories: ReadonlyArray<RedactionCategory>;
}

export interface ShareLinkRequest {
  artifact: ShareArtifact;
  artifactId: string;
  scope: ShareScope;
  /** ISO timestamp at which the link stops resolving. Required by the standard. */
  expiresAt: string;
  /** Recipient principals when scope is `named-people` or `branch-reviewers`. */
  recipients?: string[];
  redactions: RedactionPolicy;
  /** Optional human-friendly note shown to the recipient. */
  note?: string;
}

export interface ShareLink extends ShareLinkRequest {
  id: string;
  url: string;
  createdAt: string;
  /** True until `revokeShareLink` is called. */
  active: boolean;
}

export interface ShareAccessEvent {
  id: string;
  shareId: string;
  actor: string;
  occurredAt: string;
  outcome: "viewed" | "redaction-requested" | "denied" | "revoked";
}

export interface AccessLog {
  events: ShareAccessEvent[];
}

export interface ServerShareLink extends ShareLink {
  redactionBanner: string;
}

const ARTIFACT_ROUTES: Record<ShareArtifact, string> = {
  trace: "/share/trace",
  conversation: "/share/conversation",
  "eval-result": "/share/eval",
  "deploy-diff": "/share/deploy-diff",
  "parity-report": "/share/parity",
  "cost-chart": "/share/cost",
  "audit-evidence": "/share/audit",
  branch: "/share/branch",
};

function shortId(seed: string): string {
  let hash = 0;
  for (const char of seed) {
    hash = (hash * 31 + char.charCodeAt(0)) | 0;
  }
  return Math.abs(hash).toString(36).slice(0, 8);
}

/**
 * Build a share link. Pure function so callers can preview the URL before
 * persisting. The id and timestamps are deterministic when `now` is provided.
 */
export function buildShareLink(
  request: ShareLinkRequest,
  now: () => Date = () => new Date(),
): ShareLink {
  const created = now().toISOString();
  const id = `share_${shortId(`${request.artifact}:${request.artifactId}:${created}`)}`;
  const route = ARTIFACT_ROUTES[request.artifact];
  const params = new URLSearchParams({
    id: request.artifactId,
    scope: request.scope,
    expires: request.expiresAt,
  });
  if (request.redactions.categories.length > 0) {
    params.set("redact", request.redactions.categories.slice().sort().join(","));
  }
  return {
    ...request,
    id,
    url: `${route}/${id}?${params.toString()}`,
    createdAt: created,
    active: true,
  };
}

export async function createServerShareLink(
  workspaceId: string,
  request: ShareLinkRequest,
  opts: UxWireupClientOptions = {},
  now: () => Date = () => new Date(),
): Promise<ServerShareLink> {
  const local = buildShareLink(request, now);
  const expiresAtMs = new Date(request.expiresAt).getTime();
  const expiresInMinutes = Math.max(
    1,
    Math.ceil((expiresAtMs - now().getTime()) / 60_000),
  );
  const body = await cpJson<{
    id: string;
    url: string;
    expires_at: string;
    redactions: RedactionCategory[];
  }>(`/workspaces/${encodeURIComponent(workspaceId)}/shares`, {
    ...opts,
    method: "POST",
    body: {
      source_type: request.artifact,
      source_id: request.artifactId,
      expires_in_minutes: expiresInMinutes,
      redactions: request.redactions.categories,
    },
    fallback: {
      id: local.id,
      url: local.url,
      expires_at: local.expiresAt,
      redactions: [...request.redactions.categories],
    },
  });
  return {
    ...local,
    id: body.id,
    url: body.url,
    expiresAt: body.expires_at,
    redactions: { categories: body.redactions },
    redactionBanner: `${body.redactions.length} redaction categories enforced server-side.`,
  };
}

export function revokeShareLink(
  link: ShareLink,
  actor: string,
  log: AccessLog,
  now: () => Date = () => new Date(),
): { link: ShareLink; log: AccessLog } {
  const occurredAt = now().toISOString();
  return {
    link: { ...link, active: false },
    log: {
      events: [
        ...log.events,
        {
          id: `acc_${shortId(`${link.id}:${occurredAt}:revoke`)}`,
          shareId: link.id,
          actor,
          occurredAt,
          outcome: "revoked",
        },
      ],
    },
  };
}

export function recordAccess(
  link: ShareLink,
  actor: string,
  outcome: ShareAccessEvent["outcome"],
  log: AccessLog,
  now: () => Date = () => new Date(),
): AccessLog {
  const occurredAt = now().toISOString();
  return {
    events: [
      ...log.events,
      {
        id: `acc_${shortId(`${link.id}:${occurredAt}:${outcome}`)}`,
        shareId: link.id,
        actor,
        occurredAt,
        outcome,
      },
    ],
  };
}

/**
 * Apply the redaction policy to a payload string. The implementation favours
 * being explicit over clever: we mark every redacted span with a labelled
 * placeholder so the recipient can see what was redacted (section 27.5).
 */
export function previewRedaction(
  payload: string,
  redactions: RedactionPolicy,
): string {
  let output = payload;
  for (const category of redactions.categories) {
    output = REDACTORS[category](output);
  }
  return output;
}

const REDACTORS: Record<RedactionCategory, (input: string) => string> = {
  pii: (input) =>
    input
      .replace(/\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g, "[redacted: pii email]")
      .replace(/\b\+?\d[\d\s().-]{7,}\b/g, "[redacted: pii phone]")
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, "[redacted: pii ssn]"),
  secrets: (input) =>
    input
      .replace(/\b(sk|pk|rk)_[A-Za-z0-9]{8,}\b/g, "[redacted: secret]")
      .replace(/\bBearer\s+[A-Za-z0-9._-]+/gi, "[redacted: bearer]"),
  "customer-messages": (input) =>
    input.replace(/<msg>([\s\S]*?)<\/msg>/g, "<msg>[redacted: customer-message]</msg>"),
  prompts: (input) =>
    input.replace(/<prompt>([\s\S]*?)<\/prompt>/g, "<prompt>[redacted: prompt]</prompt>"),
  pricing: (input) => input.replace(/\$\s?\d+(?:[.,]\d+)?/g, "[redacted: pricing]"),
  "internal-notes": (input) =>
    input.replace(/<note>([\s\S]*?)<\/note>/g, "<note>[redacted: internal-note]</note>"),
};

/**
 * A focused review surface URL for a branch (section 27.7). Keeps Slack /
 * Linear / chat handoffs scoped to the smallest useful decision page rather
 * than dumping the reviewer into the full Studio shell.
 */
export interface QuickBranchLinkRequest {
  agentId: string;
  branch: string;
  /** Pieces of the review surface to expose; all default to true. */
  surfaces?: Partial<Record<QuickBranchSurface, boolean>>;
  baseUrl?: string;
}

export const QUICK_BRANCH_SURFACES = [
  "summary",
  "behavior-diff",
  "eval-status",
  "preflight-blockers",
  "canary",
  "actions",
] as const;

export type QuickBranchSurface = (typeof QUICK_BRANCH_SURFACES)[number];

export function buildQuickBranchLink(request: QuickBranchLinkRequest): string {
  const base = request.baseUrl ?? "/review";
  const surfaces: QuickBranchSurface[] = QUICK_BRANCH_SURFACES.filter(
    (key) => request.surfaces?.[key] !== false,
  );
  const params = new URLSearchParams({
    agent: request.agentId,
    branch: request.branch,
  });
  if (surfaces.length > 0) {
    params.set("show", surfaces.join(","));
  }
  return `${base}/${encodeURIComponent(request.agentId)}/${encodeURIComponent(
    request.branch,
  )}?${params.toString()}`;
}

export const REDACTION_LABELS: Record<RedactionCategory, string> = {
  pii: "Personally identifiable information",
  secrets: "Secrets and tokens",
  "customer-messages": "Customer messages",
  prompts: "Prompts",
  pricing: "Pricing",
  "internal-notes": "Internal notes",
};
