/**
 * S153: Topbar component shown above every authed page.
 *
 * Holds the page title slot on the left and the user menu on the
 * right. Kept as a server component so it stays cheap; only the user
 * menu opts into "use client" because it reads the Auth0 hook.
 */

import { UserMenu } from "@/components/shell/user-menu";

export function Topbar() {
  return (
    <header
      className="flex h-14 items-center justify-between border-b bg-background px-6"
      data-testid="topbar"
    >
      <span className="text-sm font-semibold tracking-tight">
        Loop Studio
      </span>
      <UserMenu />
    </header>
  );
}
