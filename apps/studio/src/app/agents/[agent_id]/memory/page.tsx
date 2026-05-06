import { MemoryStudio } from "@/components/memory/memory-studio";
import { createMemoryStudioData } from "@/lib/memory-studio";

interface AgentMemoryPageProps {
  params: { agent_id: string };
}

export default function AgentMemoryPage({ params }: AgentMemoryPageProps) {
  const data = createMemoryStudioData(params.agent_id);
  return <MemoryStudio data={data} />;
}
