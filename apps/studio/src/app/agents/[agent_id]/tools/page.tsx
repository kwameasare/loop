import { ToolsRoom } from "@/components/tools/tools-room";
import {
  createToolsRoomData,
  listAgentTools,
  type AgentTool,
} from "@/lib/agent-tools";
import { listToolContracts, type ToolContract } from "@/lib/tool-contracts";

export const dynamic = "force-dynamic";

interface AgentToolsPageProps {
  params: { agent_id: string };
}

export default async function AgentToolsPage({ params }: AgentToolsPageProps) {
  let liveTools: AgentTool[] = [];
  let toolContracts: ToolContract[] = [];
  try {
    [liveTools, toolContracts] = await Promise.all([
      listAgentTools(params.agent_id),
      listToolContracts(params.agent_id).then((result) => result.items),
    ]);
  } catch {
    liveTools = [];
    toolContracts = [];
  }
  const data = createToolsRoomData(
    params.agent_id,
    liveTools,
    undefined,
    toolContracts,
  );
  return <ToolsRoom data={data} />;
}
