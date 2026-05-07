export interface UxWireupClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

export function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
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

export async function cpJson<T>(
  path: string,
  opts: UxWireupClientOptions & {
    method?: string;
    body?: unknown;
    fallback: T;
  },
): Promise<T> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) return opts.fallback;
  const fetcher = opts.fetcher ?? fetch;
  const init: RequestInit = {
    method: opts.method ?? "GET",
    headers: cpApiHeaders(opts),
    cache: "no-store",
  };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  const response = await fetcher(`${base}${path}`, init);
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
  const wsBase = base.replace(/^http/, "ws");
  const url = new URL(`${wsBase}${path.startsWith("/") ? path : `/${path}`}`);
  if (opts.callerSub) url.searchParams.set("caller_sub", opts.callerSub);
  return url.toString();
}
