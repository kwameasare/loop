/**
 * Local-pilot login route — no Auth0, no internet required.
 *
 * Mints a HS256 JWT signed with ``LOOP_CP_LOCAL_JWT_SECRET`` (which
 * cp-api's ``HS256Verifier`` accepts on ``/v1/auth/exchange``) for
 * the supplied email, exchanges it for a PASETO session, returns the
 * pair to the browser. The browser then stashes it in
 * ``sessionStorage`` (``loop.cp.session``) so the rest of the studio
 * — which already reads from that key for Auth0 callbacks — works
 * unchanged.
 *
 * This route only runs server-side (Next.js route handler), so the
 * dev secret never reaches the client. It refuses to run in
 * ``NODE_ENV=production`` so we can't accidentally ship an
 * unauthenticated bypass.
 */

import { NextResponse } from "next/server";
import crypto from "node:crypto";

export const runtime = "nodejs";

interface DevLoginBody {
  email?: string;
}

function b64url(input: Buffer): string {
  return input
    .toString("base64")
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function mintHs256Jwt(opts: {
  secret: string;
  sub: string;
  issuer: string;
  audience: string;
  ttlSeconds?: number;
}): string {
  const ttl = opts.ttlSeconds ?? 300;
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })));
  const payload = b64url(
    Buffer.from(
      JSON.stringify({
        sub: opts.sub,
        iss: opts.issuer,
        aud: opts.audience,
        iat: now,
        exp: now + ttl,
        email: opts.sub,
      }),
    ),
  );
  const signingInput = `${header}.${payload}`;
  const sig = b64url(
    crypto.createHmac("sha256", opts.secret).update(signingInput).digest(),
  );
  return `${signingInput}.${sig}`;
}

export async function POST(request: Request): Promise<Response> {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json(
      { error: "dev-login is disabled in production" },
      { status: 404 },
    );
  }
  const secret = process.env.LOOP_CP_LOCAL_JWT_SECRET;
  if (!secret || secret.length < 16) {
    return NextResponse.json(
      {
        error:
          "LOOP_CP_LOCAL_JWT_SECRET must be set on the studio process to use dev-login",
      },
      { status: 500 },
    );
  }
  const cpApiUrl =
    process.env.LOOP_CP_API_BASE_URL ?? process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!cpApiUrl) {
    return NextResponse.json(
      { error: "LOOP_CP_API_BASE_URL not set" },
      { status: 500 },
    );
  }
  const issuer = process.env.LOOP_CP_AUTH_ISSUER ?? "https://loop.local/";
  const audience = process.env.LOOP_CP_AUTH_AUDIENCE ?? "loop-cp";

  let body: DevLoginBody = {};
  try {
    body = (await request.json()) as DevLoginBody;
  } catch {
    /* empty body OK — fall through to defaults */
  }
  const email = (body.email ?? process.env.LOOP_DEV_SEED_USER ?? "dev@loop.local").trim();
  if (!email || !email.includes("@")) {
    return NextResponse.json(
      { error: "email must look like an email address" },
      { status: 400 },
    );
  }

  const idToken = mintHs256Jwt({
    secret,
    sub: email,
    issuer,
    audience,
  });

  const exchangeUrl = `${cpApiUrl.replace(/\/$/, "")}/v1/auth/exchange`;
  const upstream = await fetch(exchangeUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
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
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(text) as Record<string, unknown>;
  } catch {
    return NextResponse.json(
      { error: "cp returned non-JSON body", body: text.slice(0, 400) },
      { status: 502 },
    );
  }

  return NextResponse.json(parsed);
}
