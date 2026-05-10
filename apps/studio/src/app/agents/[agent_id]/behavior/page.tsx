import { BehaviorEditor } from "@/components/behavior/behavior-editor";
import {
  createDegradedBehaviorEditorData,
  fetchBehaviorEditorData,
} from "@/lib/behavior";

interface AgentBehaviorPageProps {
  params: { agent_id: string };
  searchParams?: {
    sentence_id?: string | undefined;
    catch_id?: string | undefined;
  };
}

export default async function AgentBehaviorPage({
  params,
  searchParams,
}: AgentBehaviorPageProps) {
  const data = await fetchBehaviorEditorData(params.agent_id).catch((error) =>
    createDegradedBehaviorEditorData(
      params.agent_id,
      error instanceof Error ? error.message : String(error),
    ),
  );
  return (
    <BehaviorEditor
      data={data}
      initialSelectedSentenceId={searchParams?.sentence_id}
      initialCatchId={searchParams?.catch_id}
    />
  );
}
