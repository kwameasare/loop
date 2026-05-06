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
import { clearSessionToken } from "@/lib/cp-auth-exchange";

const AUTH0_CONFIGURED =
  typeof process !== "undefined" &&
  Boolean(process.env.NEXT_PUBLIC_AUTH0_DOMAIN);

export function SignInButton() {
  const auth0 = useAuth0();
  const onClick = () => {
    if (AUTH0_CONFIGURED) {
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
      disabled={AUTH0_CONFIGURED && auth0.isLoading}
      data-testid="sign-in-button"
    >
      Sign In
    </Button>
  );
}

export function SignOutButton() {
  const { logout } = useAuth0();
  const onClick = () => {
    // Drop the cp-api session token before kicking off any logout
    // flow so a same-tab "Sign In" cannot replay the prior session.
    clearSessionToken();
    if (AUTH0_CONFIGURED) {
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
