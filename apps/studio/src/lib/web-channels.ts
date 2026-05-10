/**
 * Web-channel binding helpers used by the agent "Channels" tab.
 *
 * The cp-api endpoints ``POST /v1/agents/{id}/channels/web/enable`` and
 * ``POST /v1/agents/{id}/channels/web/disable`` mint or revoke a
 * channel-scoped bearer token that the embedded ``web-channel.js``
 * script uses when calling ``/v1/agents/{id}/invoke``.
 *
 * Mutating helpers require cp-api by default. Tests and isolated demos may opt
 * into the deterministic fixture path with ``allowFixture``; route-facing code
 * must not mint local tokens that look deployable.
 */

export type WebChannelStatus = "disabled" | "enabled";

export interface WebChannelBinding {
  agentId: string;
  status: WebChannelStatus;
  channelId: string | null;
  /** Public bearer token consumed by the embed script. */
  token: string | null;
  enabledAt: string | null;
  degradedReason?: string | undefined;
}

export interface ChannelHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
  allowFixture?: boolean;
}

function resolveBase(opts: ChannelHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL
      : undefined);
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function authHeaders(opts: ChannelHelperOptions): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  return headers;
}

function localToken(): string {
  return `wct_${Math.random().toString(36).slice(2, 14)}${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

export const WEB_CHANNEL_CP_API_REQUIRED =
  "LOOP_CP_API_BASE_URL is required to load web channel.";

export async function getWebChannel(
  agentId: string,
  opts: ChannelHelperOptions = {},
): Promise<WebChannelBinding> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture !== true) {
      throw new Error(WEB_CHANNEL_CP_API_REQUIRED);
    }
    return {
      agentId,
      status: "disabled",
      channelId: null,
      token: null,
      enabledAt: null,
    };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(agentId)}/channels/web`,
    { headers: authHeaders(opts) },
  );
  if (response.status === 404) {
    return {
      agentId,
      status: "disabled",
      channelId: null,
      token: null,
      enabledAt: null,
      degradedReason:
        "cp-api web channel route returned 404. Studio will not treat an unavailable web-channel route as a deliberately disabled channel.",
    };
  }
  if (!response.ok) {
    throw new Error(
      `cp-api GET /agents/${agentId}/channels/web -> ${response.status}`,
    );
  }
  return (await response.json()) as WebChannelBinding;
}

export async function enableWebChannel(
  agentId: string,
  opts: ChannelHelperOptions = {},
): Promise<WebChannelBinding> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture !== true) {
      throw new Error(
        "LOOP_CP_API_BASE_URL is required to enable web channel.",
      );
    }
    return {
      agentId,
      status: "enabled",
      channelId: `wch_${Math.random().toString(36).slice(2, 10)}`,
      token: localToken(),
      enabledAt: new Date().toISOString(),
    };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(agentId)}/channels/web/enable`,
    { method: "POST", headers: authHeaders(opts) },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api POST /agents/${agentId}/channels/web/enable -> ${response.status}`,
    );
  }
  return (await response.json()) as WebChannelBinding;
}

export async function disableWebChannel(
  agentId: string,
  opts: ChannelHelperOptions = {},
): Promise<WebChannelBinding> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture !== true) {
      throw new Error(
        "LOOP_CP_API_BASE_URL is required to disable web channel.",
      );
    }
    return {
      agentId,
      status: "disabled",
      channelId: null,
      token: null,
      enabledAt: null,
    };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(agentId)}/channels/web/disable`,
    { method: "POST", headers: authHeaders(opts) },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api POST /agents/${agentId}/channels/web/disable -> ${response.status}`,
    );
  }
  return (await response.json()) as WebChannelBinding;
}

export interface SnippetInput {
  agentId: string;
  token: string;
  /**
   * CDN URL hosting the embed bundle. Defaults to the public Loop CDN
   * but workspaces may pin it via ``NEXT_PUBLIC_LOOP_WEB_CHANNEL_URL``.
   */
  scriptUrl?: string;
  /** Optional Loop API base URL passed through to the embed. */
  apiUrl?: string;
}

const DEFAULT_SCRIPT_URL = "https://cdn.loop.dev/web-channel/v1/web-channel.js";

export function buildEmbedSnippet(input: SnippetInput): string {
  const scriptUrl =
    input.scriptUrl ??
    (typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_LOOP_WEB_CHANNEL_URL ?? DEFAULT_SCRIPT_URL
      : DEFAULT_SCRIPT_URL);
  const apiAttr = input.apiUrl
    ? `\n  data-api-url="${escapeAttr(input.apiUrl)}"`
    : "";
  return [
    `<script async`,
    `  src="${escapeAttr(scriptUrl)}"`,
    `  data-agent-id="${escapeAttr(input.agentId)}"`,
    `  data-token="${escapeAttr(input.token)}"${apiAttr}>`,
    `</script>`,
  ].join("\n");
}

function escapeAttr(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
