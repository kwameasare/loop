import type { ReactNode } from "react";

import { AgentTabs } from "@/components/agents/agent-tabs";
import { getAgent } from "@/lib/cp-api";

export const dynamic = "force-dynamic";

interface AgentDetailLayoutProps {
  children: ReactNode;
  params: { agent_id: string };
}

/**
 * Shell layout for /agents/{agent_id}/* routes. Fetches the agent on
 * the server, renders the page header + tab nav, and slots each tab
 * route segment as `children`. Because each tab is its own segment,
 * Next.js code-splits the tab modules and lazy-loads on navigation.
 */
export default async function AgentDetailLayout({
  children,
  params,
}: AgentDetailLayoutProps) {
  const agent = await getAgent(params.agent_id);
  return (
    <main
      className="container mx-auto flex max-w-4xl flex-col gap-6 py-10"
      data-testid="agent-detail-shell"
    >
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
    </main>
  );
}
