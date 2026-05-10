import { AgentMap } from "@/components/agent-map/agent-map";
import {
  createEmptyAgentMapData,
  fetchAgentMapData,
} from "@/components/agent-map/agent-map-data";

interface AgentMapPageProps {
  params: { agent_id: string };
}

export default async function AgentMapPage({ params }: AgentMapPageProps) {
  const data = await fetchAgentMapData(params.agent_id).catch((error) =>
    createEmptyAgentMapData(
      params.agent_id,
      error instanceof Error
        ? error.message
        : "Could not load agent map instrumentation.",
    ),
  );
  return <AgentMap data={data} />;
}
