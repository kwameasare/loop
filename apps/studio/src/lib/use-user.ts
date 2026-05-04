"use client";

/**
 * S150: ``useUser()`` — the canonical identity hook for studio.
 *
 * Wraps `useAuth0` so the rest of the app depends on a stable
 * identity contract rather than the Auth0 SDK directly. Must be
 * called from a component tree wrapped in `AuthProvider`. The
 * provider degrades gracefully when Auth0 env vars are missing, so
 * tests and previews can render without configuring a tenant.
 */

import { useAuth0 } from "@auth0/auth0-react";

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

export function useUser(): UseUserResult {
  const { user, isAuthenticated, isLoading } = useAuth0();
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
}
