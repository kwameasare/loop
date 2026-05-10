import { ToolsRoom } from "@/components/tools/tools-room";
import {
  createEmptyToolsRoomData,
  createToolsRoomData,
  listAgentTools,
  type AgentTool,
} from "@/lib/agent-tools";
import { listToolContracts, type ToolContract } from "@/lib/tool-contracts";

export const dynamic = "force-dynamic";

interface AgentToolsPageProps {
  params: { agent_id: string };
  searchParams?:
    | {
        tool_contract_id?: string | string[] | undefined;
        tool_id?: string | string[] | undefined;
      }
    | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AgentToolsPage({
  params,
  searchParams,
}: AgentToolsPageProps) {
  const [toolsResult, contractsResult] = await Promise.allSettled([
    listAgentTools(params.agent_id),
    listToolContracts(params.agent_id).then((result) => result.items),
  ]);
  const liveTools: AgentTool[] =
    toolsResult.status === "fulfilled" ? toolsResult.value : [];
  const toolContracts: ToolContract[] =
    contractsResult.status === "fulfilled" ? contractsResult.value : [];
  const degradedReason = [toolsResult, contractsResult]
    .filter((result): result is PromiseRejectedResult => result.status === "rejected")
    .map((result) =>
      result.reason instanceof Error
        ? result.reason.message
        : "Tool catalog evidence could not be loaded.",
    )
    .join(" ");
  const data =
    liveTools.length > 0 || toolContracts.length > 0
      ? createToolsRoomData(
          params.agent_id,
          liveTools,
          undefined,
          toolContracts,
          degradedReason || undefined,
        )
      : createEmptyToolsRoomData(
          params.agent_id,
          degradedReason ||
            "No tools are bound yet. Paste a curl command, OpenAPI fragment, or Postman sample to draft one.",
        );
  const requestedContractId = firstParam(searchParams?.tool_contract_id);
  const requestedToolId = firstParam(searchParams?.tool_id);
  const linkedContract = requestedContractId
    ? toolContracts.find((contract) => contract.id === requestedContractId)
    : undefined;
  return (
    <ToolsRoom
      data={data}
      initialToolId={linkedContract?.tool_id ?? requestedToolId}
    />
  );
}
