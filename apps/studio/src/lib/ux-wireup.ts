import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";
import { getCpBaseUrl } from "@/lib/cp-url";

export interface UxWireupClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

export function cpApiBaseUrl(override?: string): string | null {
  // Treat an explicit override of ``""`` as "caller asked for no
  // cp" → return null. Only fall through to the env helper when
  // override is ``undefined`` (matches the original ``??`` semantics).
  if (override !== undefined) {
    if (!override) return null;
    const trimmed = override.replace(/\/$/, "");
    return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
  }
  // Browser → /api/cp/v1 (same-origin proxy). Server → real cp URL.
  try {
    return getCpBaseUrl({ withV1: true });
  } catch {
    return null;
  }
}

export function cpApiHeaders(
  opts: UxWireupClientOptions = {},
): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

function refreshBaseUrl(base: string): string {
  return base.replace(/\/v1$/, "");
}

export async function cpJson<T>(
  path: string,
  opts: UxWireupClientOptions & {
    method?: string;
    body?: unknown;
    fallback: T;
    allowFallback?: boolean;
  },
): Promise<T> {
  const fallbackEnabled = opts.allowFallback === true;
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    if (fallbackEnabled) return opts.fallback;
    throw new Error("LOOP_CP_API_BASE_URL is required for cp-api calls.");
  }
  const fetcher =
    opts.fetcher ??
    createAuthedCpApiFetch({ refreshBaseUrl: refreshBaseUrl(base) });
  const init: RequestInit = {
    method: opts.method ?? "GET",
    headers: cpApiHeaders(opts),
    cache: "no-store",
  };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  let response: Response;
  try {
    response = await fetcher(`${base}${path}`, init);
  } catch (error) {
    if (error instanceof TypeError && fallbackEnabled) return opts.fallback;
    throw error;
  }
  if (!response.ok) {
    throw new Error(`cp-api ${opts.method ?? "GET"} ${path} -> ${response.status}`);
  }
  return (await response.json()) as T;
}

export function cpWebSocketUrl(
  path: string,
  opts: { baseUrl?: string; callerSub?: string } = {},
): string | null {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) return null;
  // Same-origin proxy (browser path) returns ``/api/cp/v1`` — a
  // relative URL the WebSocket constructor can't accept. Next.js
  // Route Handlers don't support the HTTP upgrade dance either, so
  // there's nothing to connect to. Return null and let the hook
  // gracefully render in the "no live presence" state until the
  // browser is given an absolute cp URL or a real WS proxy is wired.
  if (!/^https?:\/\//i.test(base)) return null;
  const wsBase = base.replace(/^http/, "ws");
  try {
    const url = new URL(`${wsBase}${path.startsWith("/") ? path : `/${path}`}`);
    if (opts.callerSub) url.searchParams.set("caller_sub", opts.callerSub);
    return url.toString();
  } catch {
    return null;
  }
}
