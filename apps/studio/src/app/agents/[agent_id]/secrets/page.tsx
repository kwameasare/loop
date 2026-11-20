import { SecretsList } from "@/components/agents/secrets-list";
import { listAgentSecrets } from "@/lib/agent-secrets";
import { getCpAuthOptions } from "@/lib/server/session";

export const dynamic = "force-dynamic";

interface AgentSecretsPageProps {
  params: { agent_id: string };
}

export default async function AgentSecretsPage({
  params,
}: AgentSecretsPageProps) {
  const authOptions = getCpAuthOptions();
  const { items, degraded_reason } = await listAgentSecrets(
    params.agent_id,
    authOptions,
  ).catch((error: unknown) => ({
    items: [],
    degraded_reason:
      error instanceof Error
        ? `Secrets service error: ${error.message}`
        : "Secrets service error: Studio cannot verify secret references right now.",
  }));
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
