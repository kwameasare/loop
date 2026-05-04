/**
 * P0.3: cp-api fetch wrapper with a 401 → /v1/auth/refresh → retry
 * interceptor.
 *
 * The studio runs as a long-lived SPA: the access token cp-api hands
 * back from /v1/auth/exchange expires after 1h, and before this
 * wrapper shipped any cp-api call after that point would 401 and the
 * user had to do a full Auth0 re-login. The interceptor:
 *
 *   1. Calls fetch with the current access token from sessionStorage.
 *   2. On 401, checks for a refresh token; calls /v1/auth/refresh once
 *      with rotation-with-reuse-detection (cp-api revokes the supplied
 *      token and mints a fresh pair), persists the new pair, and
 *      retries the original request exactly once.
 *   3. If the refresh round-trip itself 401s — the token was reused
 *      or has been revoked — the session is cleared and the caller
 *      receives the original 401 so the UI can route to /login.
 *
 * One in-flight refresh per tab is enforced via a module-level promise
 * so 10 concurrent cp-api calls all wait on the same refresh and don't
 * stampede the endpoint (every call would otherwise revoke the
 * previous one's freshly minted token).
 */

import {
  AuthExchangeError,
  clearSessionToken,
  readSessionToken,
  refreshSessionToken,
  replaceSessionTokens,
} from "./cp-auth-exchange";

let inflightRefresh: Promise<string | null> | null = null;

/** Reset the in-flight-refresh latch. Used by tests; not a public API. */
export function __resetInflightRefreshForTests(): void {
  inflightRefresh = null;
}

async function runRefresh(baseUrl?: string, fetcher?: typeof fetch) {
  const session = readSessionToken();
  const refreshToken = session?.refresh_token;
  if (!refreshToken) return null;
  try {
    const next = await refreshSessionToken(refreshToken, {
      baseUrl,
      fetcher,
    });
    replaceSessionTokens(next);
    return next.access_token;
  } catch (err) {
    if (err instanceof AuthExchangeError && err.status === 401) {
      // Reuse-detection or expired refresh -> drop the session so the
      // app routes to /login on the next render.
      clearSessionToken();
    }
    return null;
  }
}

export interface CpApiFetchOptions {
  /** Override the cp base URL passed to /v1/auth/refresh. */
  refreshBaseUrl?: string;
  /** Override the fetch implementation (used by tests). */
  fetcher?: typeof fetch;
}

/**
 * Build a fetch wrapper that injects the current bearer token and
 * transparently retries once after a successful refresh on 401. Pass
 * the result wherever the studio would otherwise pass a raw fetch —
 * e.g. as the ``fetch`` option to the generated cp-api client.
 */
export function createAuthedCpApiFetch(
  opts: CpApiFetchOptions = {},
): typeof fetch {
  const inner = opts.fetcher ?? fetch;
  return async function authedFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    const token = readSessionToken()?.access_token ?? null;
    const initWithAuth = withBearer(init, token);
    let response = await inner(input, initWithAuth);
    if (response.status !== 401) return response;
    // Attempt one refresh-and-retry per logical call. Multiple
    // concurrent 401s share the same refresh promise so we don't
    // burn through rotated tokens.
    if (!inflightRefresh) {
      inflightRefresh = runRefresh(opts.refreshBaseUrl, inner).finally(() => {
        // Release the latch so the next 401 (likely after another
        // 1-hour window) can trigger a fresh refresh.
        inflightRefresh = null;
      });
    }
    const newAccess = await inflightRefresh;
    if (!newAccess) return response;
    response = await inner(input, withBearer(init, newAccess));
    return response;
  };
}

function withBearer(
  init: RequestInit | undefined,
  token: string | null,
): RequestInit {
  const next: RequestInit = { ...(init ?? {}) };
  // Headers can come in as Headers, [k,v][] or Record<string,string>.
  // Normalising to Record<> keeps the merge readable.
  const headers: Record<string, string> = {};
  const incoming = init?.headers;
  if (incoming instanceof Headers) {
    incoming.forEach((value, key) => {
      headers[key] = value;
    });
  } else if (Array.isArray(incoming)) {
    for (const [key, value] of incoming) headers[key] = value;
  } else if (incoming && typeof incoming === "object") {
    Object.assign(headers, incoming as Record<string, string>);
  }
  if (token) headers.authorization = `Bearer ${token}`;
  next.headers = headers;
  return next;
}
