/**
 * Server-only session readers.
 *
 * File lives under ``lib/server/`` to communicate intent: any client
 * component (or any module imported by a client component) that
 * pulls this file in will hit a build error via Next.js's
 * ``next/headers`` guard. That's intentional — the read uses
 * ``next/headers.cookies()`` which is not available in client
 * bundles.
 *
 * Server Components, Route Handlers, and Server Actions should
 * import :func:`getCpAccessToken` and pass the returned value as
 * the ``token`` arg to any ``lib/*.ts`` data function (listAgents,
 * listWorkspaces, getAgent, etc.).
 */

import { cookies } from "next/headers";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/cp-session-cookies";

/**
 * Read the studio's session access token from the current request's
 * HttpOnly cookie. Returns ``undefined`` when no cookie is set so
 * callers can spread it directly into a data-function's options
 * (``{ token: getCpAccessToken(), workspaceId }``).
 */
export function getCpAccessToken(): string | undefined {
  try {
    const value = cookies().get(ACCESS_COOKIE)?.value;
    return value && value.length > 0 ? value : undefined;
  } catch {
    // `cookies()` throws when called outside a request context
    // (e.g. during a static prerender at build time). Treat that
    // as anonymous and let the caller render in degraded mode.
    return undefined;
  }
}

export function getCpAuthOptions(): { token: string } | Record<string, never> {
  const token = getCpAccessToken();
  return token ? { token } : {};
}

/**
 * Read the refresh-token cookie. Used only by
 * ``/api/session/refresh``.
 */
export function getCpRefreshToken(): string | undefined {
  try {
    const value = cookies().get(REFRESH_COOKIE)?.value;
    return value && value.length > 0 ? value : undefined;
  } catch {
    return undefined;
  }
}
