import { FlowEditor } from "@/components/flow/flow-editor";

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
          Visual flow editor for agent <code>{params.agent_id}</code>. Drag
          nodes from the palette to compose the flow.
        </p>
      </header>
      <FlowEditor agentId={params.agent_id} />
    </main>
  );
}
