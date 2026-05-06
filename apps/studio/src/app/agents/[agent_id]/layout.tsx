import type { ReactNode } from "react";

import { getAgentDetailData } from "./agent-detail-data";
import { AgentTabs } from "@/components/agents/agent-tabs";
import { EmulatorPanel } from "@/components/agents/emulator-panel";

export const dynamic = "force-dynamic";

interface AgentDetailLayoutProps {
  children: ReactNode;
  params: { agent_id: string };
}

/**
 * Shell layout for /agents/{agent_id}/* routes. Fetches the agent on
 * the server, renders the page header + tab nav, and slots each tab
 * route segment as `children`. The right rail hosts the emulator
 * (sticky on wide viewports) so editors can probe the agent while
 * reviewing its config.
 */
export default async function AgentDetailLayout({
  children,
  params,
}: AgentDetailLayoutProps) {
  const { agent } = await getAgentDetailData(params.agent_id);
  return (
    <main
      className="container mx-auto grid max-w-6xl gap-6 py-10 lg:grid-cols-[minmax(0,1fr)_360px]"
      data-testid="agent-detail-shell"
    >
      <div className="flex min-w-0 flex-col gap-6">
        <header className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            Agent
          </p>
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="text-3xl font-semibold tracking-tight">
              {agent.name || "Untitled agent"}
            </h1>
            <code className="text-sm text-muted-foreground">{agent.slug}</code>
          </div>
          {agent.description ? (
            <p className="text-muted-foreground">{agent.description}</p>
          ) : null}
        </header>
        <AgentTabs agentId={params.agent_id} />
        <section data-testid="agent-tab-content">{children}</section>
      </div>
      <aside
        className="lg:sticky lg:top-10 lg:max-h-[calc(100vh-5rem)]"
        data-testid="agent-emulator-rail"
      >
        <EmulatorPanel agentId={params.agent_id} />
      </aside>
    </main>
  );
}
