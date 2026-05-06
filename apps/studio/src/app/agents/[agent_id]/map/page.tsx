import { AgentMap } from "@/components/agent-map/agent-map";
import { createAgentMapData } from "@/components/agent-map/agent-map-data";

interface AgentMapPageProps {
  params: { agent_id: string };
}

export default function AgentMapPage({ params }: AgentMapPageProps) {
  const data = createAgentMapData(params.agent_id);
  return <AgentMap data={data} />;
}
