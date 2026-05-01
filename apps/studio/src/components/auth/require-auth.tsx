"use client";

/**
 * S151: Protected route guard.
 *
 * Wraps a sub-tree that requires an authenticated user. On mount we
 * read `useUser()`; if Auth0 says the visitor is anonymous we send
 * them to ``/login?returnTo=<current-path>`` and the login page
 * forwards `returnTo` into the Auth0 PKCE flow's `appState` so the
 * post-callback redirect lands the user back where they came from.
 *
 * Renders a small placeholder while Auth0 is still resolving the
 * session so the protected content does not flash.
 */

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useUser } from "@/lib/use-user";

interface RequireAuthProps {
  children: ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, isLoading } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      const returnTo = encodeURIComponent(pathname || "/");
      router.replace(`/login?returnTo=${returnTo}`);
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <main
        className="flex min-h-screen items-center justify-center"
        role="status"
        aria-label="Checking session"
      >
        <p className="text-muted-foreground">Checking session…</p>
      </main>
    );
  }

  return <>{children}</>;
}
