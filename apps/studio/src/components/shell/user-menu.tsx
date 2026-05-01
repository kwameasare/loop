"use client";

/**
 * S153: User menu shown in the topbar.
 *
 * Displays the signed-in user's avatar (initial fallback) and a sign
 * out trigger. We piggy-back on the auth0-react ``logout`` helper via
 * the shared ``SignOutButton`` so the redirect URL stays consistent
 * with the sign-in flow defined in S150.
 */

import { useUser } from "@/lib/use-user";
import { SignOutButton } from "@/components/auth/sign-in-button";

function initial(name: string | undefined, email: string | undefined): string {
  const source = (name || email || "?").trim();
  return (source[0] ?? "?").toUpperCase();
}

export function UserMenu() {
  const { user, isAuthenticated } = useUser();
  if (!isAuthenticated || !user) return null;
  const display = user.name || user.email || "Signed in";
  return (
    <div className="flex items-center gap-3" data-testid="user-menu">
      <div
        aria-hidden="true"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-sm font-semibold"
      >
        {initial(user.name, user.email)}
      </div>
      <span className="text-sm font-medium" data-testid="user-display">
        {display}
      </span>
      <SignOutButton />
    </div>
  );
}
