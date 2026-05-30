/**
 * One place to ask "where do I send a cp-api request from here?".
 *
 * In the browser (client components, ``"use client"``): the answer
 * is always the same-origin proxy at ``/api/cp``. The browser never
 * talks to cp directly — see ``/api/cp/[...path]/route.ts``.
 *
 * On the server (Server Components, Route Handlers, Server
 * Actions): the answer is the actual cp address from
 * ``LOOP_CP_API_BASE_URL`` (falls back to
 * ``NEXT_PUBLIC_LOOP_API_URL`` for older dev setups).
 *
 * Callers should not need to special-case the environment — this
 * helper makes the right choice and ``cp-api-fetch.ts`` /
 * generated-client wiring just feeds the URL forward.
 */

const BROWSER_PROXY_BASE = "/api/cp";

/**
 * Return the cp-api base URL appropriate for the current execution
 * context. Optionally appends ``/v1`` if not already present so the
 * generated client picks up its prefix.
 *
 * Production browser → ``/api/cp`` (same-origin proxy).
 * Production server  → ``LOOP_CP_API_BASE_URL`` env.
 * Vitest             → respects ``NEXT_PUBLIC_LOOP_API_URL`` so the
 *                      existing data-layer tests keep asserting on
 *                      direct cp URLs (vitest never spins up the
 *                      Next.js proxy).
 */
export function getCpBaseUrl(opts: { withV1?: boolean } = {}): string {
  const withV1 = opts.withV1 ?? false;
  const isBrowser = typeof window !== "undefined";
  // Vitest exposes ``VITEST=true``; treat that as "not a real
  // browser" so unit tests can still inspect the upstream cp URL.
  const isVitest =
    typeof process !== "undefined" &&
    (process.env?.VITEST === "true" || process.env?.NODE_ENV === "test");
  let base: string;
  if (isBrowser && !isVitest) {
    base = BROWSER_PROXY_BASE;
  } else {
    const raw =
      process.env.LOOP_CP_API_BASE_URL ??
      process.env.NEXT_PUBLIC_LOOP_API_URL ??
      "";
    if (!raw) {
      throw new Error(
        "LOOP_CP_API_BASE_URL (or NEXT_PUBLIC_LOOP_API_URL) must be set on the server",
      );
    }
    base = raw.replace(/\/$/, "");
  }
  if (!withV1) return base;
  return base.endsWith("/v1") ? base : `${base}/v1`;
}
