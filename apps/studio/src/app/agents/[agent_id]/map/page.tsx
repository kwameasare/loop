import { AgentMap } from "@/components/agent-map/agent-map";
import {
  createEmptyAgentMapData,
  fetchAgentMapData,
} from "@/components/agent-map/agent-map-data";

interface AgentMapPageProps {
  params: { agent_id: string };
}

export default async function AgentMapPage({ params }: AgentMapPageProps) {
  const data = await fetchAgentMapData(params.agent_id).catch(() =>
    createEmptyAgentMapData(params.agent_id),
  );
  return <AgentMap data={data} />;
}
