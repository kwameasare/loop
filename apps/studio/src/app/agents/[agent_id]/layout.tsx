import type { ReactNode } from "react";

import {
  agentProductionLabel,
  agentWorkbenchTopbarFacts,
  agentStateLabel,
  agentStateSentence,
  getAgentDetailData,
} from "./agent-detail-data";
import { AgentEvidenceRail } from "@/components/agents/agent-evidence-rail";
import { AgentTestDrawer } from "@/components/agents/agent-test-drawer";
import { AgentTabs } from "@/components/agents/agent-tabs";
import { AgentWorkbenchControls } from "@/components/agents/agent-workbench-controls";
import { listAgentWorkflow } from "@/lib/agent-workflow";
import { getCpAuthOptions } from "@/lib/server/session";

export const dynamic = "force-dynamic";

interface AgentDetailLayoutProps {
  children: ReactNode;
  params: { agent_id: string };
}

/**
 * Shell layout for /agents/{agent_id}/* routes. Fetches the agent on
 * the server, renders the page header + tab nav, and slots each tab
 * route segment as `children`. The right rail stays compact: evidence links
 * and test entry points only. Full simulation lives in the simulator tab and
 * the in-page test drawer so the work surface keeps priority.
 */
export default async function AgentDetailLayout({
  children,
  params,
}: AgentDetailLayoutProps) {
  const authOptions = getCpAuthOptions();
  const { agent, degradedReason } = await getAgentDetailData(params.agent_id);
  const workflow = await listAgentWorkflow(params.agent_id, authOptions).catch(
    () => undefined,
  );
  const productionLabel = agentProductionLabel(agent);
  const stateLabel = agentStateLabel(agent);
  const topbarFacts = agentWorkbenchTopbarFacts(agent, workflow);
  return (
    <main
      className="container mx-auto grid max-w-7xl gap-5 py-6 lg:grid-cols-[minmax(0,1fr)_16rem]"
      data-testid="agent-detail-shell"
    >
      <div className="flex min-w-0 flex-col gap-6">
        <header
          className="instrument-panel rounded-2xl p-4"
          data-testid="agent-local-topbar"
        >
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Agent Workbench
              </p>
              <h1 className="mt-1 break-words text-2xl font-semibold tracking-tight">
                {agent.name || "Untitled agent"}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <code className="break-all">{agent.slug}</code>
                <span aria-hidden>·</span>
                <span>Production {productionLabel}</span>
                <span aria-hidden>·</span>
                <span>State {stateLabel}</span>
                <span aria-hidden>·</span>
                <span className="break-all">
                  Evidence {agent.state_evidence_ref}
                </span>
              </div>
              <p
                className="mt-3 max-w-3xl text-sm text-foreground"
                data-testid="agent-state-sentence"
              >
                {agentStateSentence(agent)}
              </p>
            </div>
            <AgentWorkbenchControls
              agentId={params.agent_id}
              disabledReason={
                degradedReason
                  ? "Live agent data is unavailable. Reconnect the control-plane session before changing this agent."
                  : undefined
              }
            />
          </div>
          <dl
            className="mt-4 grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,9rem),1fr))]"
            data-testid="agent-local-topbar-facts"
          >
            {topbarFacts.map((fact) => (
              <div
                key={fact.id}
                className="rounded-md border bg-background/70 px-2.5 py-2"
                data-testid={`agent-topbar-fact-${fact.id}`}
                title={`Evidence: ${fact.evidence}`}
              >
                <dt className="text-[0.68rem] font-semibold uppercase tracking-wide text-muted-foreground">
                  {fact.label}
                </dt>
                <dd className="mt-1 truncate text-xs font-medium text-foreground">
                  {fact.value}
                </dd>
              </div>
            ))}
          </dl>
          <div
            className="quiet-scrollbar mt-4 overflow-x-auto border-t pt-3"
            data-testid="agent-local-nav"
          >
            <AgentTabs agentId={params.agent_id} orientation="horizontal" />
          </div>
        </header>
        <section data-testid="agent-tab-content">{children}</section>
        <AgentTestDrawer agentId={params.agent_id} />
      </div>
      <aside
        className="lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)]"
        data-testid="agent-emulator-rail"
      >
        <AgentEvidenceRail
          agentId={params.agent_id}
          degradedReason={degradedReason}
        />
      </aside>
    </main>
  );
}
