import type { ReactNode } from "react";

import {
  agentProductionLabel,
  agentStateLabel,
  agentStateSentence,
  getAgentDetailData,
} from "./agent-detail-data";
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
  const productionLabel = agentProductionLabel(agent);
  const stateLabel = agentStateLabel(agent);
  return (
    <main
      className="container mx-auto grid max-w-7xl gap-6 py-8 lg:grid-cols-[15rem_minmax(0,1fr)_22rem]"
      data-testid="agent-detail-shell"
    >
      <aside
        className="min-w-0 space-y-4 lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:overflow-auto"
        data-testid="agent-local-nav"
      >
        <div className="rounded-md border bg-card p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Agent Workbench
          </p>
          <h1 className="mt-2 break-words text-lg font-semibold">
            {agent.name || "Untitled agent"}
          </h1>
          <code className="mt-1 block break-all text-xs text-muted-foreground">
            {agent.slug}
          </code>
        </div>
        <AgentTabs agentId={params.agent_id} orientation="vertical" />
      </aside>
      <div className="flex min-w-0 flex-col gap-6">
        <header
          className="rounded-md border bg-card p-4"
          data-testid="agent-local-topbar"
        >
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Production {productionLabel}</span>
            <span aria-hidden>·</span>
            <span>State {stateLabel}</span>
            <span aria-hidden>·</span>
            <span className="break-all">
              Evidence {agent.state_evidence_ref}
            </span>
          </div>
          <p
            className="mt-2 text-sm text-foreground"
            data-testid="agent-state-sentence"
          >
            {agentStateSentence(agent)}
          </p>
        </header>
        <section data-testid="agent-tab-content">{children}</section>
      </div>
      <aside
        className="lg:sticky lg:top-10 lg:max-h-[calc(100vh-5rem)]"
        data-testid="agent-emulator-rail"
      >
        <EmulatorPanel agentId={params.agent_id} evidenceMode="empty" />
      </aside>
    </main>
  );
}
