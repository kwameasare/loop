"use client";

/**
 * S151: ``/login`` — kicks off the Auth0 PKCE redirect.
 *
 * Reads ``returnTo`` from the query string and forwards it into the
 * Auth0 redirect's ``appState`` so ``onRedirectCallback`` (configured
 * in the AuthProvider) can route the user back after authentication.
 *
 * Already-signed-in users skip the round-trip and go straight to
 * ``returnTo`` (or ``/``). The inner component is wrapped in a
 * Suspense boundary because ``useSearchParams`` forces a client-side
 * bailout during static prerender.
 */

import { useAuth0 } from "@auth0/auth0-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { useUser } from "@/lib/use-user";

function LoginInner() {
  const { loginWithRedirect } = useAuth0();
  const { isAuthenticated, isLoading } = useUser();
  const router = useRouter();
  const params = useSearchParams();
  const returnTo = params.get("returnTo") || "/";

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.replace(returnTo);
      return;
    }
    void loginWithRedirect({ appState: { returnTo } });
  }, [isLoading, isAuthenticated, loginWithRedirect, returnTo, router]);

  return (
    <main
      className="flex min-h-screen items-center justify-center"
      role="status"
      aria-label="Redirecting to sign in"
    >
      <p className="text-muted-foreground">Redirecting to sign in…</p>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main
          className="flex min-h-screen items-center justify-center"
          role="status"
          aria-label="Loading"
        >
          <p className="text-muted-foreground">Loading…</p>
        </main>
      }
    >
      <LoginInner />
    </Suspense>
  );
}
