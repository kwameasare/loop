import { BehaviorEditor } from "@/components/behavior/behavior-editor";
import {
  createEmptyBehaviorEditorData,
  fetchBehaviorEditorData,
} from "@/lib/behavior";

interface AgentBehaviorPageProps {
  params: { agent_id: string };
}

export default async function AgentBehaviorPage({ params }: AgentBehaviorPageProps) {
  const data = await fetchBehaviorEditorData(params.agent_id).catch(() =>
    createEmptyBehaviorEditorData(params.agent_id),
  );
  return <BehaviorEditor data={data} />;
}
