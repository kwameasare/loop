import type { ReactNode } from "react";
import { ActivityTimeline } from "@/components/shell/activity-timeline";
import { LivePreviewRail } from "@/components/shell/live-preview-rail";
import { SidebarNav } from "@/components/shell/sidebar-nav";
import { StatusFooter } from "@/components/shell/status-footer";
import { Topbar } from "@/components/shell/topbar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
      <div
        className="grid min-h-screen grid-cols-1 bg-background text-foreground lg:grid-cols-[max-content_minmax(0,1fr)_23rem] lg:grid-rows-[auto_minmax(0,1fr)_auto_auto]"
        data-testid="app-shell"
      >
        <aside
          className="border-b bg-surface lg:row-span-4 lg:w-72 lg:min-w-64 lg:max-w-96 lg:resize-x lg:overflow-auto lg:border-b-0 lg:border-r"
          aria-label="Asset rail"
          data-testid="asset-rail"
        >
        <SidebarNav />
      </aside>
      <div className="lg:col-span-2">
        <Topbar />
      </div>
      <section
        className="min-w-0 overflow-auto bg-background"
        aria-label="Studio work surface"
        data-testid="work-surface"
      >
        {children}
      </section>
      <LivePreviewRail />
      <div className="lg:col-span-2">
        <ActivityTimeline />
      </div>
      <div className="lg:col-span-2">
        <StatusFooter />
      </div>
    </div>
  );
}
