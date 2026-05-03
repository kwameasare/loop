/**
 * S912: client-side helper for the cp-api ``/v1/auth/exchange``
 * endpoint.
 *
 * After @auth0/auth0-react finishes the PKCE round-trip we hand the
 * Auth0 ID token to cp-api which mints a short-lived Loop session
 * token (PASETO) plus a refresh token. The studio stores the session
 * token in ``sessionStorage`` so a tab refresh reuses it but a closed
 * tab requires a fresh login.
 */

export interface AuthExchangeResponse {
  access_token: string;
  token_type?: string;
  expires_in?: number;
  refresh_token?: string;
  session_token?: string;
}

export class AuthExchangeError extends Error {
  status: number;
  body: string;

  constructor(message: string, status: number, body: string) {
    super(message);
    this.name = "AuthExchangeError";
    this.status = status;
    this.body = body;
  }
}

const SESSION_STORAGE_KEY = "loop.cp.session";

export interface ExchangeOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
}

function resolveBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.NEXT_PUBLIC_LOOP_API_URL ??
    process.env.LOOP_CP_API_BASE_URL;
  if (!raw) {
    throw new Error(
      "NEXT_PUBLIC_LOOP_API_URL is required to call /v1/auth/exchange"
    );
  }
  return raw.replace(/\/$/, "");
}

/**
 * POST the Auth0 id_token to cp-api ``/v1/auth/exchange`` and return
 * the Loop session token. Throws :class:`AuthExchangeError` on a
 * 4xx/5xx response so callers can surface a meaningful error in the UI.
 */
export async function exchangeAuth0Token(
  idToken: string,
  options: ExchangeOptions = {}
): Promise<AuthExchangeResponse> {
  const fetcher = options.fetcher ?? fetch;
  const url = `${resolveBaseUrl(options.baseUrl)}/v1/auth/exchange`;
  const response = await fetcher(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
    cache: "no-store",
  });
  const text = await response.text();
  if (!response.ok) {
    throw new AuthExchangeError(
      `cp-api /v1/auth/exchange returned ${response.status}`,
      response.status,
      text
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new AuthExchangeError(
      "cp-api /v1/auth/exchange returned non-JSON body",
      response.status,
      text
    );
  }
  if (!parsed || typeof parsed !== "object") {
    throw new AuthExchangeError(
      "cp-api /v1/auth/exchange returned non-object body",
      response.status,
      text
    );
  }
  return parsed as AuthExchangeResponse;
}

export function storeSessionToken(payload: AuthExchangeResponse): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        access_token: payload.access_token,
        session_token: payload.session_token ?? payload.access_token,
        expires_in: payload.expires_in ?? null,
        token_type: payload.token_type ?? "Bearer",
        stored_at: Date.now(),
      })
    );
  } catch {
    // sessionStorage unavailable (e.g. private mode); ignore -- the
    // SPA will simply re-exchange on the next callback.
  }
}

export function clearSessionToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function readSessionToken(): {
  access_token: string;
  session_token: string;
  expires_in: number | null;
  token_type: string;
  stored_at: number;
} | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    if (typeof parsed.access_token !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export const __SESSION_STORAGE_KEY_FOR_TESTS__ = SESSION_STORAGE_KEY;
