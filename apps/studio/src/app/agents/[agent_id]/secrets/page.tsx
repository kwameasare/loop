import { SecretsList } from "@/components/agents/secrets-list";
import { listAgentSecrets } from "@/lib/agent-secrets";

export const dynamic = "force-dynamic";

interface AgentSecretsPageProps {
  params: { agent_id: string };
}

export default async function AgentSecretsPage({
  params,
}: AgentSecretsPageProps) {
  const { items, degraded_reason } = await listAgentSecrets(params.agent_id);
  return (
    <div data-testid="agent-secrets">
      <SecretsList
        agentId={params.agent_id}
        initialSecrets={items}
        degradedReason={degraded_reason}
      />
    </div>
  );
}
