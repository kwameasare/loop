/**
 * /api/session — session lifecycle for the studio.
 *
 * - ``POST /api/session`` : exchange an Auth0 ID token for a Loop
 *   PASETO via cp's ``/v1/auth/exchange``, then set HttpOnly
 *   ``loop.cp.access`` + ``loop.cp.refresh`` cookies. Returns the
 *   tokens in the body so client-side code can also cache them in
 *   ``sessionStorage`` for direct cp fetches.
 *
 * - ``DELETE /api/session`` : clears both cookies. The browser-side
 *   sign-out clears ``sessionStorage`` separately; this route is the
 *   server-side half of logout.
 *
 * The cp base URL is read from ``LOOP_CP_API_BASE_URL`` (server-only)
 * with ``NEXT_PUBLIC_LOOP_API_URL`` as a fallback for dev. The cp URL
 * is NEVER exposed to the browser — every cp call goes through this
 * server route.
 */
import { NextResponse } from "next/server";

import {
  clearCpSessionCookies,
  setCpSessionCookies,
  type CpSessionExchangeResponse,
} from "@/lib/cp-session-cookies";

export const runtime = "nodejs";

interface PostBody {
  id_token?: string;
}

function cpApiUrl(): string {
  const raw =
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL ??
    "";
  if (!raw) {
    throw new Error(
      "LOOP_CP_API_BASE_URL (or NEXT_PUBLIC_LOOP_API_URL) must be set",
    );
  }
  return raw.replace(/\/$/, "");
}

export async function POST(request: Request): Promise<Response> {
  let body: PostBody = {};
  try {
    body = (await request.json()) as PostBody;
  } catch {
    return NextResponse.json(
      { error: "request body must be JSON" },
      { status: 400 },
    );
  }
  if (typeof body.id_token !== "string" || body.id_token.length < 16) {
    return NextResponse.json(
      { error: "id_token is required" },
      { status: 400 },
    );
  }
  const upstream = await fetch(`${cpApiUrl()}/v1/auth/exchange`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ id_token: body.id_token }),
    cache: "no-store",
  });
  const text = await upstream.text();
  if (!upstream.ok) {
    return NextResponse.json(
      {
        error: `cp /v1/auth/exchange failed: HTTP ${upstream.status}`,
        upstream_body: text.slice(0, 400),
      },
      { status: 502 },
    );
  }
  let parsed: CpSessionExchangeResponse;
  try {
    parsed = JSON.parse(text) as CpSessionExchangeResponse;
  } catch {
    return NextResponse.json(
      { error: "cp returned non-JSON body", body: text.slice(0, 400) },
      { status: 502 },
    );
  }
  // Build the JSON response first so we can attach Set-Cookie headers
  // to the same object (avoids two NextResponse instances).
  const response = NextResponse.json(parsed);
  setCpSessionCookies(response.cookies, parsed);
  return response;
}

export async function DELETE(): Promise<Response> {
  const response = NextResponse.json({ ok: true });
  clearCpSessionCookies(response.cookies);
  return response;
}
