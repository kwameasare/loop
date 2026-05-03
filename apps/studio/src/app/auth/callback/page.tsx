"use client";

/**
 * S150 + S912: Auth0 callback page.
 *
 * `@auth0/auth0-react` handles the PKCE code exchange transparently
 * when the SDK initialises on a URL containing `?code=` & `?state=`.
 *
 * Once the SDK reports an authenticated user (S912) we hand the Auth0
 * ID token to cp-api ``/v1/auth/exchange`` which mints a short-lived
 * Loop session token. The session token is stored in
 * ``sessionStorage`` so subsequent fetches against cp-api can carry
 * ``Authorization: Bearer <session>``.
 */

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth0 } from "@auth0/auth0-react";
import { useUser } from "@/lib/use-user";
import {
  AuthExchangeError,
  exchangeAuth0Token,
  storeSessionToken,
} from "@/lib/cp-auth-exchange";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useUser();
  const { getIdTokenClaims } = useAuth0();
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
            ""
          );
        }
        const session = await exchangeAuth0Token(idToken);
        storeSessionToken(session);
        if (!cancelled) router.replace("/");
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Sign-in failed";
        setError(message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoading, isAuthenticated, getIdTokenClaims, router]);

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
