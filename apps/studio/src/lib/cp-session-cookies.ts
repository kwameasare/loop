/**
 * Studio ↔ cp session cookie plumbing — writer + constants.
 *
 * Read helpers (which need ``next/headers.cookies()``) live in
 * ``lib/server/session.ts`` so this module stays free of the
 * server-only import chain. Keeping the writer side here lets Route
 * Handlers (``/api/session``, ``/api/session/refresh``,
 * ``/api/dev-login``) share one cookie shape without dragging
 * ``next/headers`` into client bundles.
 *
 * Cookies:
 *
 * - ``loop.cp.access``  — short-lived PASETO access token. Sent on
 *   every request to cp via ``Authorization: Bearer`` (forwarded by
 *   Server Components); refreshed silently when it expires.
 * - ``loop.cp.refresh`` — long-lived refresh-token. Only ever read
 *   by the ``/api/session/refresh`` Route Handler.
 *
 * Both are HttpOnly + SameSite=Lax + Path=/ + Secure when
 * NODE_ENV=production. Same-site is sufficient because the browser
 * only ever hits Next.js (same origin); cp is reached server-side.
 *
 * NOTE: this module uses ``NextResponse.cookies`` (server-only API
 * from ``next/server``) but does NOT import ``next/headers``, so it
 * doesn't get tagged with the "server-only" build flag that bars
 * client imports. Even so, it has no client-side use, so importing
 * it from a "use client" component is almost certainly a mistake.
 */

export const ACCESS_COOKIE = "loop.cp.access";
export const REFRESH_COOKIE = "loop.cp.refresh";

/** Default access TTL when cp doesn't report one (defensive). */
const DEFAULT_ACCESS_MAX_AGE_SECONDS = 60 * 60;
/** Default refresh TTL when cp doesn't report one (defensive). */
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

export interface CpSessionExchangeResponse {
  access_token: string;
  refresh_token?: string | null;
  access_expires_at_ms?: number;
  refresh_expires_at_ms?: number;
  token_type?: string;
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function maxAgeFromExpiresAtMs(
  expiresAtMs: number | undefined,
  fallbackSeconds: number,
): number {
  if (!expiresAtMs) return fallbackSeconds;
  const diff = Math.floor((expiresAtMs - Date.now()) / 1000);
  // Refuse to set a cookie that's already expired — that would clear it.
  return diff > 0 ? diff : fallbackSeconds;
}

interface CookieJar {
  set(name: string, value: string, options: Record<string, unknown>): void;
}

/**
 * Write both session cookies on the given jar. Use from Route
 * Handlers via ``cookies()`` from ``next/headers`` (App Router) or
 * from the ``NextResponse.cookies`` API.
 */
export function setCpSessionCookies(
  jar: CookieJar,
  exchange: CpSessionExchangeResponse,
): void {
  const accessMaxAge = maxAgeFromExpiresAtMs(
    exchange.access_expires_at_ms,
    DEFAULT_ACCESS_MAX_AGE_SECONDS,
  );
  jar.set(ACCESS_COOKIE, exchange.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: isProduction(),
    path: "/",
    maxAge: accessMaxAge,
  });
  if (exchange.refresh_token) {
    const refreshMaxAge = maxAgeFromExpiresAtMs(
      exchange.refresh_expires_at_ms,
      DEFAULT_REFRESH_MAX_AGE_SECONDS,
    );
    jar.set(REFRESH_COOKIE, exchange.refresh_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: isProduction(),
      path: "/",
      maxAge: refreshMaxAge,
    });
  }
}

/** Clear both cookies — for logout + auth-failure paths. */
export function clearCpSessionCookies(jar: CookieJar): void {
  jar.set(ACCESS_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isProduction(),
    path: "/",
    maxAge: 0,
  });
  jar.set(REFRESH_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isProduction(),
    path: "/",
    maxAge: 0,
  });
}
