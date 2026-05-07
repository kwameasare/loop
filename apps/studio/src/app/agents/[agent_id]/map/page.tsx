import { AgentMap } from "@/components/agent-map/agent-map";
import {
  createAgentMapData,
  fetchAgentMapData,
} from "@/components/agent-map/agent-map-data";

interface AgentMapPageProps {
  params: { agent_id: string };
}

export default async function AgentMapPage({ params }: AgentMapPageProps) {
  const data = await fetchAgentMapData(params.agent_id).catch(() =>
    createAgentMapData(params.agent_id),
  );
  return <AgentMap data={data} />;
}
