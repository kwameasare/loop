/**
 * S153: App shell wrapping every authed studio page.
 *
 * Layout:
 *   [ Sidebar | (Topbar / Content) ]
 *
 * The sidebar is fixed at 240px on md+ screens and collapses on
 * mobile (the basic markup keeps the structure responsive without
 * pulling in a drawer library). Pages render inside ``<main>``.
 */

import type { ReactNode } from "react";
import { SidebarNav } from "@/components/shell/sidebar-nav";
import { Topbar } from "@/components/shell/topbar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      data-testid="app-shell"
    >
      <aside className="border-b bg-muted/40 md:w-60 md:border-b-0 md:border-r">
        <SidebarNav />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
