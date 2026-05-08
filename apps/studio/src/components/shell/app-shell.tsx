import type { ReactNode } from "react";
import { PointerDelight } from "@/components/shell/pointer-delight";
import { SidebarNav } from "@/components/shell/sidebar-nav";
import { Topbar } from "@/components/shell/topbar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div
      className="grid min-h-screen grid-cols-1 bg-background/88 text-foreground lg:grid-cols-[max-content_minmax(0,1fr)] lg:grid-rows-[auto_minmax(0,1fr)]"
      data-testid="app-shell"
    >
      <PointerDelight />
      <aside
        className="quiet-scrollbar border-b bg-surface/86 shadow-[inset_-1px_0_0_hsl(var(--foreground)/0.03)] backdrop-blur-xl lg:row-span-2 lg:w-72 lg:min-w-64 lg:max-w-80 lg:resize-x lg:overflow-auto lg:border-b-0 lg:border-r"
        aria-label="Workspace navigation"
        data-testid="asset-rail"
      >
        <SidebarNav />
      </aside>
      <div>
        <Topbar />
      </div>
      <section
        className="page-enter quiet-scrollbar min-w-0 overflow-auto bg-background/72"
        aria-label="Studio work surface"
        data-testid="work-surface"
      >
        {children}
      </section>
    </div>
  );
}
