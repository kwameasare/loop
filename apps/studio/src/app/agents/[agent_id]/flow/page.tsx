import { FlowCanvas } from "@/components/flow/flow-canvas";

export const dynamic = "force-dynamic";

export default function FlowPage({
  params,
}: {
  params: { agent_id: string };
}): JSX.Element {
  return (
    <main className="container mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight">Flow</h1>
        <p className="text-muted-foreground text-sm">
          Visual flow editor for agent <code>{params.agent_id}</code>. The
          blank canvas with pan/zoom is the foundation; nodes and edges land
          in S461.
        </p>
      </header>
      <FlowCanvas agentId={params.agent_id} />
    </main>
  );
}
