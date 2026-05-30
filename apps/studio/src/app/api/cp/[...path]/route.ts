/**
 * /api/cp/* — same-origin proxy to cp-api.
 *
 * The browser never talks to cp directly. Every studio-side fetch
 * goes here:
 *
 *   browser → /api/cp/v1/workspaces
 *                  │
 *                  ├─ reads loop.cp.access cookie (HttpOnly)
 *                  ├─ adds Authorization: Bearer <token>
 *                  ├─ strips host-private headers (cookie, host, …)
 *                  └─ → cp /v1/workspaces (server-side)
 *
 * Why a proxy instead of direct browser→cp:
 *
 * - **No CORS** — the browser only sees same-origin requests.
 * - **No cross-origin cookies** — the session cookie set on the
 *   studio's origin can't be sent to cp's origin in a same-site
 *   setup; routing through Next.js keeps cookie auth working.
 * - **No cp URL on the client** — the runtime cp address isn't
 *   exposed to the browser; cp can move (or be IP-restricted)
 *   without re-deploying the studio bundle.
 * - **One auth surface** — there's exactly one place that converts
 *   the cookie into a bearer.
 *
 * Streaming: we use ``fetch`` and pipe ``response.body`` straight
 * through to the caller. That preserves Server-Sent Events from
 * cp's ``POST /v1/agents/{id}/test-turn`` and any future streaming
 * endpoints without buffering them server-side.
 */

import { type NextRequest, NextResponse } from "next/server";

import { getCpAccessToken } from "@/lib/server/session";

export const runtime = "nodejs";
// Forward dynamic segments — never let Next.js attempt to cache.
export const dynamic = "force-dynamic";

function cpBase(): string {
  const raw =
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL ??
    "";
  if (!raw) {
    throw new Error(
      "LOOP_CP_API_BASE_URL (or NEXT_PUBLIC_LOOP_API_URL) must be set to proxy to cp-api",
    );
  }
  return raw.replace(/\/$/, "");
}

// Headers we never forward to cp because they describe the
// studio↔browser hop, not the studio↔cp hop, or they leak host-
// private state (cookies, host, etc.).
const _HOP_BY_HOP = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "upgrade",
  // Cookie is the studio's session cookie — cp doesn't speak
  // cookie auth, only Authorization.
  "cookie",
  // The browser may set its own Authorization (e.g. transitional
  // sessionStorage path); we authoritatively replace it with the
  // bearer derived from the HttpOnly session cookie.
  "authorization",
]);

function buildForwardHeaders(request: NextRequest): Headers {
  const out = new Headers();
  request.headers.forEach((value, key) => {
    if (!_HOP_BY_HOP.has(key.toLowerCase())) {
      out.set(key, value);
    }
  });
  const token = getCpAccessToken();
  if (token) out.set("authorization", `Bearer ${token}`);
  return out;
}

async function proxy(
  request: NextRequest,
  params: { path: string[] },
): Promise<Response> {
  const subPath = params.path.join("/");
  const search = request.nextUrl.search; // already includes leading ?
  const url = `${cpBase()}/${subPath}${search}`;
  const headers = buildForwardHeaders(request);

  // Body: pass through for verbs that can have one. ``GET``/``HEAD``
  // never carry bodies. Use ``request.body`` (a ReadableStream) so
  // we don't buffer multi-MB uploads in memory; we ALSO have to set
  // ``duplex: 'half'`` per the Fetch spec for streaming bodies in
  // Node's undici client.
  const method = request.method.toUpperCase();
  const hasBody = !["GET", "HEAD"].includes(method);
  const init: RequestInit & { duplex?: "half" } = {
    method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };
  if (hasBody) {
    init.body = request.body;
    init.duplex = "half";
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch (exc) {
    return NextResponse.json(
      {
        error: "cp unreachable",
        detail: exc instanceof Error ? exc.message : String(exc),
      },
      { status: 502 },
    );
  }

  // Strip hop-by-hop headers on the way back too.
  const respHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!_HOP_BY_HOP.has(key.toLowerCase())) respHeaders.set(key, value);
  });
  // Use ``upstream.body`` (ReadableStream) so SSE / chunked
  // responses stream straight through to the browser.
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

interface RouteContext {
  params: { path: string[] };
}

export async function GET(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function POST(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function PUT(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function PATCH(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function DELETE(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function OPTIONS(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
export async function HEAD(
  request: NextRequest,
  ctx: RouteContext,
): Promise<Response> {
  return proxy(request, ctx.params);
}
