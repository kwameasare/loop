import { BehaviorEditor } from "@/components/behavior/behavior-editor";
import { createBehaviorEditorData, fetchBehaviorEditorData } from "@/lib/behavior";

interface AgentBehaviorPageProps {
  params: { agent_id: string };
}

export default async function AgentBehaviorPage({ params }: AgentBehaviorPageProps) {
  const data = await fetchBehaviorEditorData(params.agent_id).catch(() =>
    createBehaviorEditorData(params.agent_id),
  );
  return <BehaviorEditor data={data} />;
}
