import { ConductorStudio } from "@/components/conductor/conductor-studio";
import { createConductorData } from "@/lib/conductor";

interface AgentConductorPageProps {
  params: { agent_id: string };
}

export default function AgentConductorPage({
  params,
}: AgentConductorPageProps) {
  const data = createConductorData(params.agent_id);
  return <ConductorStudio data={data} />;
}
