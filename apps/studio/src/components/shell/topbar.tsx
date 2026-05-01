/**
 * S153: Topbar component shown above every authed page.
 *
 * Holds the workspace switcher on the left and the user menu on the
 * right. Kept as a server component so it stays cheap; only the
 * children opt into "use client".
 */

import { UserMenu } from "@/components/shell/user-menu";
import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";

export function Topbar() {
  return (
    <header
      className="flex h-14 items-center justify-between border-b bg-background px-6"
      data-testid="topbar"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-tight">
          Loop Studio
        </span>
        <WorkspaceSwitcher />
      </div>
      <UserMenu />
    </header>
  );
}
