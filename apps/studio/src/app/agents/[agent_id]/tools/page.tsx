import { ToolsRoom } from "@/components/tools/tools-room";
import {
  createToolsRoomData,
  listAgentTools,
  type AgentTool,
} from "@/lib/agent-tools";

export const dynamic = "force-dynamic";

interface AgentToolsPageProps {
  params: { agent_id: string };
}

export default async function AgentToolsPage({ params }: AgentToolsPageProps) {
  let liveTools: AgentTool[] = [];
  try {
    liveTools = await listAgentTools(params.agent_id);
  } catch {
    liveTools = [];
  }
  const data = createToolsRoomData(params.agent_id, liveTools);
  return <ToolsRoom data={data} />;
}
