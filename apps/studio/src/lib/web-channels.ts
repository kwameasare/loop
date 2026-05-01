/**
 * Web-channel binding helpers used by the agent "Channels" tab.
 *
 * The cp-api endpoints ``POST /v1/agents/{id}/channels/web/enable`` and
 * ``POST /v1/agents/{id}/channels/web/disable`` mint or revoke a
 * channel-scoped bearer token that the embedded ``web-channel.js``
 * script uses when calling ``/v1/agents/{id}/invoke``.
 *
 * If no cp-api base URL is configured the helpers fall back to an
 * in-memory mock so the UX can still be reviewed end-to-end. Tests pin
 * ``baseUrl`` to exercise the live fetch path.
 */

export type WebChannelStatus = "disabled" | "enabled";

export interface WebChannelBinding {
  agentId: string;
  status: WebChannelStatus;
  channelId: string | null;
  /** Public bearer token consumed by the embed script. */
  token: string | null;
  enabledAt: string | null;
}

export interface ChannelHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
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

export async function getWebChannel(
  agentId: string,
  opts: ChannelHelperOptions = {},
): Promise<WebChannelBinding> {
  const base = resolveBase(opts);
  if (!base) {
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
