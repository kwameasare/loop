"use client";

/**
 * S150: Sign In / Sign Out controls.
 *
 * Calls `loginWithRedirect` (PKCE flow under the hood) so clicking
 * "Sign In" sends the browser to the Auth0 universal login. After
 * the round-trip Auth0 redirects back to `/auth/callback` where the
 * SDK exchanges the code for tokens and `useUser()` starts returning
 * the identity.
 */

import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import { clearSessionToken } from "@/lib/cp-auth-exchange";

export function SignInButton() {
  const { loginWithRedirect, isLoading } = useAuth0();
  return (
    <Button
      onClick={() => loginWithRedirect()}
      disabled={isLoading}
      data-testid="sign-in-button"
    >
      Sign In
    </Button>
  );
}

export function SignOutButton() {
  const { logout } = useAuth0();
  return (
    <Button
      variant="outline"
      onClick={() => {
        // S912: drop the cp-api session token before kicking off the
        // Auth0 logout redirect so a same-tab "Sign In" cannot replay
        // the prior session.
        clearSessionToken();
        const returnTo =
          typeof window !== "undefined" ? window.location.origin : undefined;
        void logout({
          logoutParams: {
            ...(returnTo ? { returnTo } : {}),
          },
        });
      }}
      data-testid="sign-out-button"
    >
      Sign Out
    </Button>
  );
}
