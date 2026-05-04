/**
 * P0.3: agent tools tab.
 *
 * Lists every tool currently bound to the agent. Wires
 * ``GET /v1/agents/{agent_id}/tools`` (cp shim blocked; falls back
 * to an empty catalog on 404). Replaces the previous static stub.
 */

import { listAgentTools } from "@/lib/agent-tools";
import { ToolsList } from "@/components/agents/tools-list";

export const dynamic = "force-dynamic";

interface AgentToolsPageProps {
  params: { agent_id: string };
}

export default async function AgentToolsPage({ params }: AgentToolsPageProps) {
  const tools = await listAgentTools(params.agent_id);
  return (
    <div className="flex flex-col gap-4" data-testid="agent-tools">
      <header>
        <h2 className="text-lg font-medium">Tools</h2>
        <p className="text-sm text-muted-foreground">
          MCP and HTTP tools bound to this agent. Bindings flow through the
          control plane; this page reflects the live state.
        </p>
      </header>
      <ToolsList tools={tools} />
    </div>
  );
}
