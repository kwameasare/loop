import { BehaviorEditor } from "@/components/behavior/behavior-editor";
import { createBehaviorEditorData } from "@/lib/behavior";

interface AgentBehaviorPageProps {
  params: { agent_id: string };
}

export default function AgentBehaviorPage({ params }: AgentBehaviorPageProps) {
  const data = createBehaviorEditorData(params.agent_id);
  return <BehaviorEditor data={data} />;
}
