/**
 * Enterprise SSO tab — IdP connection helpers (S615).
 *
 * Provides types and a fixture-backed ``postIdpMetadata`` function for
 * the enterprise IdP-connect panel.
 *
 * The control plane endpoint is ``POST /v1/enterprise/idp/metadata``.
 * In production it accepts either:
 *   - ``{ url: string }``   — metadata URL (fetched server-side)
 *   - ``{ xml: string }``   — raw XML text
 *
 * After a successful upload the workspace status transitions from
 * ``not_configured`` → ``pending_verification``.  Once the tenant
 * completes a successful ACS round-trip (SP-initiated login that
 * passes all validators) the control plane flips the status to
 * ``connected``.
 *
 * This module owns both the real API call (used in production) and the
 * FIXTURE data (used by tests and the local dev server).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Current IdP connection status for a workspace. */
export type IdpConnectionStatus =
  | "not_configured"
  | "pending_verification"
  | "connected";

/** Metadata source — exactly one key must be present. */
export type IdpMetadataSource =
  | { url: string; xml?: never }
  | { xml: string; url?: never };

/** What the POST /v1/enterprise/idp/metadata endpoint returns. */
export interface IdpConnectionResponse {
  status: IdpConnectionStatus;
  entity_id: string | null;
  acs_url: string | null;
  /** ISO 8601 timestamp of the last successful ACS round-trip; null if never. */
  connected_at: string | null;
}

// ---------------------------------------------------------------------------
// Fixtures (used in tests and the stub server)
// ---------------------------------------------------------------------------

export const FIXTURE_IDP_NOT_CONFIGURED: IdpConnectionResponse = {
  status: "not_configured",
  entity_id: null,
  acs_url: null,
  connected_at: null,
};

export const FIXTURE_IDP_PENDING: IdpConnectionResponse = {
  status: "pending_verification",
  entity_id: "https://dev.okta.com/app/fixture/entity",
  acs_url: "https://app.loop.dev/auth/saml/acs/ws-fixture",
  connected_at: null,
};

export const FIXTURE_IDP_CONNECTED: IdpConnectionResponse = {
  status: "connected",
  entity_id: "https://dev.okta.com/app/fixture/entity",
  acs_url: "https://app.loop.dev/auth/saml/acs/ws-fixture",
  connected_at: "2026-05-01T12:00:00Z",
};

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

export interface PostIdpMetadataOptions {
  source: IdpMetadataSource;
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

/**
 * Upload IdP metadata to the control plane.
 *
 * Throws on network failures or non-2xx responses.
 */
export async function postIdpMetadata(
  opts: PostIdpMetadataOptions,
): Promise<IdpConnectionResponse> {
  const raw =
    opts.baseUrl ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required to post IdP metadata");
  }
  const base = raw.replace(/\/$/, "").replace(/\/v1$/, "");
  const url = `${base}/v1/enterprise/idp/metadata`;

  const fetcher = opts.fetcher ?? fetch;
  const body: Record<string, string> = "url" in opts.source
    ? { url: opts.source.url }
    : { xml: opts.source.xml };

  const res = await fetcher(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`IdP metadata upload failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<IdpConnectionResponse>;
}

// ---------------------------------------------------------------------------
// Group → role mapping rules (S617)
// ---------------------------------------------------------------------------

/** Loop workspace roles in descending privilege order. */
export const WORKSPACE_ROLES = [
  "owner",
  "admin",
  "editor",
  "operator",
  "viewer",
] as const;

export type WorkspaceRole = (typeof WORKSPACE_ROLES)[number];

/** A single group → role mapping row. */
export interface GroupRuleRow {
  /** IdP group name exactly as it appears in the SAML ``groups`` attribute. */
  group: string;
  /** Loop workspace role to grant. */
  role: WorkspaceRole;
}

/** Response from GET/PUT /v1/enterprise/group-rules */
export interface GroupRulesResponse {
  workspace_id: string;
  rules: GroupRuleRow[];
}

/** Fixtures */
export const FIXTURE_GROUP_RULES_EMPTY: GroupRulesResponse = {
  workspace_id: "ws-fixture",
  rules: [],
};

export const FIXTURE_GROUP_RULES_SAMPLE: GroupRulesResponse = {
  workspace_id: "ws-fixture",
  rules: [
    { group: "admins", role: "admin" },
    { group: "editors", role: "editor" },
    { group: "viewers", role: "viewer" },
  ],
};

export interface PutGroupRulesOptions {
  workspaceId: string;
  rules: GroupRuleRow[];
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

/**
 * Persist group→role rules to the control plane.
 *
 * PUT /v1/enterprise/group-rules replaces the entire rule set for the
 * workspace (upsert semantics).
 */
export async function putGroupRules(
  opts: PutGroupRulesOptions,
): Promise<GroupRulesResponse> {
  const raw =
    opts.baseUrl ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required to put group rules");
  }
  const base = raw.replace(/\/$/, "").replace(/\/v1$/, "");
  const url = `${base}/v1/enterprise/group-rules`;

  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    body: JSON.stringify({
      workspace_id: opts.workspaceId,
      rules: opts.rules,
    }),
  });

  if (!res.ok) {
    throw new Error(`Group rules update failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<GroupRulesResponse>;
}

