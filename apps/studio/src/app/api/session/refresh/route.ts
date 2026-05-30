/**
 * /api/session/refresh — silent token rotation.
 *
 * Reads the HttpOnly ``loop.cp.refresh`` cookie, calls cp's
 * ``/v1/auth/refresh``, sets fresh ``loop.cp.access`` +
 * ``loop.cp.refresh`` cookies, and returns the new access token in
 * the body so the client can update its in-memory copy.
 *
 * Triggered by ``createAuthedCpApiFetch`` when it sees a 401 from
 * cp. The refresh-family revoke-detection lives in cp itself; this
 * route is a thin proxy.
 */
import { NextResponse } from "next/server";

import {
  clearCpSessionCookies,
  setCpSessionCookies,
  type CpSessionExchangeResponse,
} from "@/lib/cp-session-cookies";
import { getCpRefreshToken } from "@/lib/server/session";

export const runtime = "nodejs";

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

export async function POST(): Promise<Response> {
  const refresh = getCpRefreshToken();
  if (!refresh) {
    const response = NextResponse.json(
      { error: "no refresh token cookie" },
      { status: 401 },
    );
    // Clear any half-set state so the next request starts clean.
    clearCpSessionCookies(response.cookies);
    return response;
  }
  const upstream = await fetch(`${cpApiUrl()}/v1/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
    cache: "no-store",
  });
  const text = await upstream.text();
  if (!upstream.ok) {
    // cp's refresh-family revoke-on-reuse will fire 401 here when
    // the refresh token has been used twice or revoked. Wipe the
    // cookies so the client is forced back through Auth0.
    const response = NextResponse.json(
      {
        error: `cp /v1/auth/refresh failed: HTTP ${upstream.status}`,
        upstream_body: text.slice(0, 400),
      },
      { status: upstream.status === 401 ? 401 : 502 },
    );
    clearCpSessionCookies(response.cookies);
    return response;
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
  const response = NextResponse.json(parsed);
  setCpSessionCookies(response.cookies, parsed);
  return response;
}
