"use client";

/**
 * S150: Auth0 SDK provider for the studio frontend.
 *
 * Wraps the App Router shell with `Auth0Provider` configured for
 * PKCE + refresh tokens. Configuration is read from `NEXT_PUBLIC_*`
 * environment variables so the same bundle ships against dev /
 * staging / prod tenants.
 *
 * If the configuration is missing the provider degrades gracefully in
 * dev/test/preview by rendering children without an Auth0 context —
 * `useUser()` then returns the anonymous shape (`isAuthenticated:
 * false`). In **production** (NODE_ENV === "production") missing
 * config raises so a misconfigured deploy fails loudly at boot rather
 * than silently shipping an unauthenticated studio.
 */

import { Auth0Provider, type AppState } from "@auth0/auth0-react";
import type { ReactNode } from "react";

export interface AuthProviderProps {
  children: ReactNode;
  /** Override env vars; primarily used by tests. */
  config?: {
    domain?: string;
    clientId?: string;
    audience?: string;
    redirectUri?: string;
  };
  /**
   * Override the env used to gate the production fail-loud check.
   * Tests pass ``"production"`` to assert the gate; production
   * deploys leave this unset so it falls back to ``process.env``.
   */
  envName?: string;
}

function readConfig(override?: AuthProviderProps["config"]) {
  const domain = override?.domain ?? process.env.NEXT_PUBLIC_AUTH0_DOMAIN ?? "";
  const clientId =
    override?.clientId ?? process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID ?? "";
  const audience =
    override?.audience ?? process.env.NEXT_PUBLIC_AUTH0_AUDIENCE ?? undefined;
  const redirectUri =
    override?.redirectUri ??
    (typeof window !== "undefined"
      ? `${window.location.origin}/auth/callback`
      : undefined);
  return { domain, clientId, audience, redirectUri };
}

export function AuthProvider({ children, config, envName }: AuthProviderProps) {
  const { domain, clientId, audience, redirectUri } = readConfig(config);
  if (!domain || !clientId) {
    const env = envName ?? process.env.NODE_ENV;
    if (env === "production") {
      // Fail loud: production must boot with Auth0 wired or no studio
      // at all. The previous silent fallthrough shipped an
      // unauthenticated studio when env vars were missing.
      throw new Error(
        "AuthProvider: NEXT_PUBLIC_AUTH0_DOMAIN and NEXT_PUBLIC_AUTH0_CLIENT_ID are required in production",
      );
    }
    // Allow the studio to render without Auth0 wired (tests, preview).
    return <>{children}</>;
  }
  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      // PKCE is the default for SPAs in @auth0/auth0-react v2; we make
      // the intent explicit here so reviewers don't have to guess.
      authorizationParams={{
        redirect_uri: redirectUri,
        audience,
        scope: "openid profile email offline_access",
      }}
      useRefreshTokens
      cacheLocation="memory"
      // S151: route the user back to ``appState.returnTo`` (set by
      // /login) after the post-callback round-trip.
      onRedirectCallback={(appState?: AppState) => {
        if (typeof window === "undefined") return;
        const target = appState?.returnTo;
        if (typeof target === "string" && target.startsWith("/")) {
          window.history.replaceState({}, document.title, target);
        }
      }}
    >
      {children}
    </Auth0Provider>
  );
}
