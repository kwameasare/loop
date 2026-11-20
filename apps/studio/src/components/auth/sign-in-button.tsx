"use client";

/**
 * S150: Sign In / Sign Out controls.
 *
 * Auth0 path: ``loginWithRedirect`` kicks off the PKCE flow so the
 * browser redirects to Auth0 universal login. After the round-trip
 * Auth0 redirects back to ``/auth/callback`` where the SDK exchanges
 * the code for tokens.
 *
 * Local-pilot path (no Auth0 configured): the buttons just navigate
 * to ``/login`` (which renders the email-only form) and clear the
 * cp-api session from sessionStorage on sign-out.
 */

import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import { useAuth0Configured } from "@/lib/auth-mode";
import { clearSessionToken } from "@/lib/cp-auth-exchange";

export function SignInButton() {
  const auth0 = useAuth0();
  const auth0Configured = useAuth0Configured();
  const onClick = () => {
    if (auth0Configured) {
      void auth0.loginWithRedirect();
      return;
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };
  return (
    <Button
      onClick={onClick}
      disabled={auth0Configured && auth0.isLoading}
      data-testid="sign-in-button"
    >
      Sign In
    </Button>
  );
}

export function SignOutButton() {
  const { logout } = useAuth0();
  const auth0Configured = useAuth0Configured();
  const onClick = async () => {
    // Drop the cp-api session token before kicking off any logout
    // flow so a same-tab "Sign In" cannot replay the prior session.
    clearSessionToken();
    await fetch("/api/session", { method: "DELETE" }).catch(() => {
      /* best-effort cookie cleanup */
    });
    if (auth0Configured) {
      const returnTo =
        typeof window !== "undefined" ? window.location.origin : undefined;
      void logout({
        logoutParams: {
          ...(returnTo ? { returnTo } : {}),
        },
      });
      return;
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };
  return (
    <Button variant="outline" onClick={onClick} data-testid="sign-out-button">
      Sign Out
    </Button>
  );
}
