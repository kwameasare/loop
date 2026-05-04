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

// ---------------------------------------------------------------------------
// Workspace-scoped SAML configuration (P0.3)
// ---------------------------------------------------------------------------
//
// The audit doc identifies ``/v1/workspaces/{id}/enterprise/saml`` as
// the canonical workspace-scoped SSO route. cp-api has the underlying
// ``saml*.py`` service modules but no FastAPI shim is mounted yet, so
// these helpers degrade on 404: GET returns ``not_configured`` so the
// page can render the "set me up" panel, POST surfaces a clear error
// telling the user the route hasn't shipped.

export interface SamlConfigResponse {
  status: IdpConnectionStatus;
  entity_id: string | null;
  /** Workspace-specific ACS URL the IdP will POST SAMLResponses to. */
  acs_url: string | null;
  connected_at: string | null;
}

export interface PostSamlConfigBody {
  metadata_url?: string;
  metadata_xml?: string;
}

interface SamlClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function _samlBase(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) throw new Error("LOOP_CP_API_BASE_URL is required for SAML calls");
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

/**
 * Read the SAML config for a workspace.
 *
 * Blocked on cp-api PR. Returns ``not_configured`` on 404 so the
 * page renders cleanly today and lights up automatically when
 * cp ships ``/v1/workspaces/{id}/enterprise/saml``.
 */
export async function fetchSamlConfig(
  workspace_id: string,
  opts: SamlClientOptions = {},
): Promise<SamlConfigResponse> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${_samlBase(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/enterprise/saml`;
  const res = await fetcher(url, { method: "GET", headers, cache: "no-store" });
  if (res.status === 404) {
    return {
      status: "not_configured",
      entity_id: null,
      acs_url: null,
      connected_at: null,
    };
  }
  if (!res.ok) throw new Error(`cp-api GET enterprise/saml -> ${res.status}`);
  return (await res.json()) as SamlConfigResponse;
}

/** Save SAML config. Returns the cp response or throws on non-2xx. */
export async function postSamlConfig(
  workspace_id: string,
  body: PostSamlConfigBody,
  opts: SamlClientOptions = {},
): Promise<SamlConfigResponse> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${_samlBase(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/enterprise/saml`;
  const res = await fetcher(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(
      `cp-api POST enterprise/saml -> ${res.status}` +
        (res.status === 404
          ? " (route not yet shipped; blocked on cp-api PR)"
          : ""),
    );
  }
  return (await res.json()) as SamlConfigResponse;
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

