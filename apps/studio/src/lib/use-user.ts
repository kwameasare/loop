"use client";

/**
 * S150: ``useUser()`` — the canonical identity hook for studio.
 *
 * Wraps `useAuth0` when Auth0 is configured, falls back to reading
 * the cp-api session from ``sessionStorage`` only when Auth0 is not
 * configured (local pilot mode). The studio's ``/login`` page handles both shapes:
 * Auth0 PKCE if configured, an email-only ``POST /api/dev-login``
 * otherwise.
 *
 * Without this fallback, ``useAuth0()`` outside an Auth0Provider
 * returns ``isLoading: true`` forever and every ``RequireAuth``-gated
 * page hangs on "Checking session…". The AuthProvider degrades
 * gracefully (renders children with no Auth0Provider) when the env
 * vars are missing, but it still throws in NODE_ENV=production so
 * a misconfigured prod deploy fails loudly at boot.
 */

import { useEffect, useMemo, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useAuth0Configured } from "@/lib/auth-mode";
import { readSessionToken } from "@/lib/cp-auth-exchange";

export interface User {
  sub: string;
  email?: string;
  name?: string;
  picture?: string;
}

export interface UseUserResult {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

/** Same key used by ``cp-auth-exchange.ts``. Exported as a constant
 * so the local-pilot login + the storage-event listener stay in sync. */
const SESSION_STORAGE_KEY = "loop.cp.session";

interface DecodedClaims {
  sub: string;
  email?: string;
  name?: string;
  exp?: number;
}

/** Decode the body of a PASETO-or-JWT-shaped string for display only.
 * ``access_token`` from cp's local exchange is a PASETO v4.local — a
 * 5-segment token with a base64url payload at index 1. Anything else
 * we just probe defensively; if decoding fails we fall back to a
 * synthetic dev user."""
 */
function decodeAccessToken(token: string): DecodedClaims | null {
  try {
    const parts = token.split(".");
    if (parts.length < 3) return null;
    // PASETO v4.local: ["v4", "local", base64url(payload), ...]
    const candidate = parts[2];
    if (!candidate) return null;
    const padded = candidate + "=".repeat((4 - (candidate.length % 4)) % 4);
    const decoded = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    // Try to JSON-parse; if it fails, the token is opaque (encrypted
    // PASETO local mode) and we just return null.
    const obj = JSON.parse(decoded) as DecodedClaims;
    return typeof obj === "object" && obj !== null ? obj : null;
  } catch {
    return null;
  }
}

function localUserFromSession(): User | null {
  const session = readSessionToken();
  if (!session?.access_token) return null;
  if (session.user?.sub) {
    return {
      sub: session.user.sub,
      ...(session.user.email ? { email: session.user.email } : {}),
      ...(session.user.name ? { name: session.user.name } : {}),
      ...(session.user.picture ? { picture: session.user.picture } : {}),
    };
  }
  const claims = decodeAccessToken(session.access_token);
  // Even if decode fails, the presence of a session token means the
  // user signed in via dev-login. Fall back to a generic dev user.
  if (!claims?.sub) {
    return {
      sub: "dev-pilot",
      email: process.env.LOOP_DEV_SEED_USER ?? "dev@loop.local",
      name: "Pilot User",
    };
  }
  return {
    sub: claims.sub,
    ...(claims.email ? { email: claims.email } : {}),
    ...(claims.name ? { name: claims.name } : { name: claims.sub }),
  };
}

function useLocalSession(): UseUserResult {
  // Keep the first client render aligned with SSR. Reading
  // sessionStorage before hydration makes protected routes swap from
  // "Checking session…" on the server to authenticated content on the
  // client and trips a root hydration error. The effect below is still
  // deterministic: it synchronously reads the stored cp-api session on
  // mount, then listens for cross-tab updates.
  const [state, setState] = useState<{
    hydrated: boolean;
    user: User | null;
  }>({ hydrated: false, user: null });

  useEffect(() => {
    setState({ hydrated: true, user: localUserFromSession() });
    function onStorage(event: StorageEvent) {
      if (event.key !== SESSION_STORAGE_KEY) return;
      setState({ hydrated: true, user: localUserFromSession() });
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return useMemo<UseUserResult>(
    () => ({
      user: state.user,
      isAuthenticated: Boolean(state.user),
      isLoading: !state.hydrated,
    }),
    [state],
  );
}

function useAuth0Session(): UseUserResult {
  const { user, isAuthenticated, isLoading } = useAuth0();
  return useMemo<UseUserResult>(() => {
    if (!user || !user.sub) {
      return { user: null, isAuthenticated, isLoading };
    }
    return {
      user: {
        sub: user.sub,
        ...(user.email ? { email: user.email } : {}),
        ...(user.name ? { name: user.name } : {}),
        ...(user.picture ? { picture: user.picture } : {}),
      },
      isAuthenticated,
      isLoading,
    };
  }, [user, isAuthenticated, isLoading]);
}

export function useUser(): UseUserResult {
  // Hooks must run unconditionally — call both, return one. The
  // unused branch is cheap (just reads from useAuth0's context or a
  // single useEffect on mount).
  const auth0Configured = useAuth0Configured();
  const auth0 = useAuth0Session();
  const local = useLocalSession();
  if (!auth0Configured) return local;
  if (auth0.isAuthenticated) return auth0;
  if (local.isLoading) {
    return { user: null, isAuthenticated: false, isLoading: true };
  }
  if (!local.isAuthenticated) return auth0;
  // The Auth0 SDK keeps its token cache in memory. A full page reload can
  // therefore leave the Studio with valid Loop session cookies plus a mirrored
  // cp session in sessionStorage while Auth0 reports anonymous until the next
  // redirect. Treat that cp session as a UI guard only; all real data still
  // goes through the server-side HttpOnly cookie or the cp-api proxy.
  return local;
}
