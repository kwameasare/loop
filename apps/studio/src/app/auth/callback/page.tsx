"use client";

/**
 * S150: Auth0 callback page.
 *
 * `@auth0/auth0-react` handles the code exchange transparently when
 * the SDK initialises on a URL containing `?code=` & `?state=`.
 * This page simply renders a placeholder during that round-trip and
 * redirects back to "/" once the user is authenticated.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/lib/use-user";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useUser();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground" role="status">
        Completing sign-in…
      </p>
    </main>
  );
}
