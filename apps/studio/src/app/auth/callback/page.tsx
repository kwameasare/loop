"use client";

/**
 * Auth0 callback page.
 *
 * ``@auth0/auth0-react`` handles the PKCE code exchange transparently
 * when the SDK initialises on a URL containing ``?code=`` &
 * ``?state=``. Once the SDK reports an authenticated user we POST
 * the Auth0 ID token to ``/api/session`` (a Next.js Route Handler
 * that calls cp's ``/v1/auth/exchange`` server-side). The handler
 * sets HttpOnly ``loop.cp.access`` + ``loop.cp.refresh`` cookies so
 * Server Components can authenticate against cp, and returns the
 * tokens in the body so client-side code can also cache them in
 * ``sessionStorage`` for direct browser→cp fetches.
 *
 * Why we don't call cp directly any more: the previous
 * sessionStorage-only flow left Server Components (e.g. ``/home``,
 * ``/agents``) unable to authenticate — they ran on the Next.js
 * server with no access to the browser's storage and ended up
 * rendering "Agent registry unavailable". The cookie path closes
 * that gap without putting long-lived service tokens in env vars.
 */

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth0 } from "@auth0/auth0-react";
import { useUser } from "@/lib/use-user";
import {
  AuthExchangeError,
  storeSessionToken,
  type AuthExchangeResponse,
} from "@/lib/cp-auth-exchange";

function readSafeReturnTo(): string {
  if (typeof window === "undefined") return "/home";
  const target = new URLSearchParams(window.location.search).get("returnTo");
  return target && target.startsWith("/") && !target.startsWith("//")
    ? target
    : "/home";
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useUser();
  const { getIdTokenClaims, user: auth0User } = useAuth0();
  const exchangedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading || !isAuthenticated || exchangedRef.current) return;
    exchangedRef.current = true;

    let cancelled = false;
    void (async () => {
      try {
        const claims = await getIdTokenClaims();
        const idToken = claims?.__raw;
        if (!idToken) {
          throw new AuthExchangeError(
            "Auth0 returned no id_token after PKCE exchange",
            0,
            "",
          );
        }
        // POST to the BFF Route Handler — it talks to cp server-side
        // and writes the HttpOnly cookies that SSR auth needs.
        const response = await fetch("/api/session", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ id_token: idToken }),
        });
        if (!response.ok) {
          const text = await response.text();
          throw new AuthExchangeError(
            `/api/session returned HTTP ${response.status}`,
            response.status,
            text,
          );
        }
        const session = (await response.json()) as AuthExchangeResponse;
        // Mirror to sessionStorage for client-side fetches that still
        // read it directly (channel forms, test-turn widget, etc.).
        storeSessionToken(session, auth0User);
        if (!cancelled) {
          router.replace(readSafeReturnTo());
          // The target route may have rendered once before `/api/session`
          // wrote the HttpOnly cp cookie. Force a fresh RSC fetch so
          // agent/workspace server components re-run with the real session.
          router.refresh();
        }
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Sign-in failed";
        setError(message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoading, isAuthenticated, getIdTokenClaims, auth0User, router]);

  if (error) {
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        role="alert"
      >
        <div className="space-y-2 text-center">
          <p className="text-destructive font-medium" data-testid="auth-error">
            Sign-in failed: {error}
          </p>
          <button
            type="button"
            className="text-sm underline"
            onClick={() => router.replace("/login")}
          >
            Try again
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground" role="status">
        Completing sign-in…
      </p>
    </main>
  );
}
