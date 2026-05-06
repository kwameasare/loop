"use client";

/**
 * S150: ``useUser()`` — the canonical identity hook for studio.
 *
 * Wraps `useAuth0` when Auth0 is configured, falls back to reading
 * the cp-api session from ``sessionStorage`` when it isn't (local
 * pilot mode). The studio's ``/login`` page handles both shapes:
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

const AUTH0_CONFIGURED =
  typeof process !== "undefined" &&
  Boolean(process.env.NEXT_PUBLIC_AUTH0_DOMAIN);

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
  // Synchronous initial state: on the client, read sessionStorage
  // during first render so we never report ``isLoading: true`` past
  // the initial mount. The previous version used an
  // ``hydrated``-flag + ``useEffect`` dance, but under React Strict
  // Mode (Next.js dev double-render) the effect race meant the
  // "Checking session…" placeholder could stick around. This shape
  // matches what ``cp-auth-exchange`` already does in
  // ``readSessionToken`` (returns null on the server, real value on
  // the client) so SSR gets ``user: null`` and the client mount
  // immediately re-renders with the real value.
  const [user, setUser] = useState<User | null>(() => localUserFromSession());

  useEffect(() => {
    // Re-read on mount in case the client-only sessionStorage read
    // returned different data than the SSR hydration assumed.
    setUser(localUserFromSession());
    function onStorage(event: StorageEvent) {
      if (event.key !== SESSION_STORAGE_KEY) return;
      setUser(localUserFromSession());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return useMemo<UseUserResult>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      // No "loading" state for the local path — sessionStorage is
      // synchronous. RequireAuth either redirects to /login (no
      // session) or renders children (session present), no
      // intermediate "checking" placeholder.
      isLoading: false,
    }),
    [user],
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
  const auth0 = useAuth0Session();
  const local = useLocalSession();
  return AUTH0_CONFIGURED ? auth0 : local;
}
