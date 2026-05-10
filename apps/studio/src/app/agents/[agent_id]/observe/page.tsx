import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import {
  buildObservatoryModel,
  type ObservatoryModel,
} from "@/lib/observatory";
import { fetchUsageRecords, monthBoundsUTC } from "@/lib/costs";
import { listInbox } from "@/lib/inbox";
import { listAgentIncidents } from "@/lib/incidents";
import { searchTraces } from "@/lib/traces";
import { getAgentDetailData } from "../agent-detail-data";

interface PageProps {
  params: { agent_id: string };
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function emptyModel(args: {
  workspaceId: string;
  degradedReason?: string | undefined;
}): ObservatoryModel {
  return buildObservatoryModel({
    workspaceId: args.workspaceId,
    traces: [],
    usage: [],
    inbox: [],
    incidents: [],
    nowMs: Date.now(),
    degradedReason: args.degradedReason,
  });
}

export default async function AgentObservabilityPage({ params }: PageProps) {
  const { agent, degradedReason: agentDegradedReason } =
    await getAgentDetailData(params.agent_id);
  const workspaceId = agent.workspace_id;

  if (!workspaceId || workspaceId === "unavailable") {
    return (
      <section data-testid="agent-observability-page">
        <ObservatoryScreen
          model={emptyModel({
            workspaceId: "unavailable",
            degradedReason:
              agentDegradedReason ??
              "Workspace context is unavailable, so Studio cannot request agent-scoped observability evidence.",
          })}
        />
      </section>
    );
  }

  const nowMs = Date.now();
  const month = monthBoundsUTC(nowMs);
  const degradedReasons: string[] = [];
  if (agentDegradedReason) degradedReasons.push(agentDegradedReason);

  const [traces, usage, inbox, incidents] = await Promise.all([
    searchTraces(workspaceId, {
      agent_id: params.agent_id,
      page_size: 100,
    })
      .then((result) => result.traces)
      .catch((error: unknown) => {
        degradedReasons.push(
          messageFromError(error, "Could not load agent traces."),
        );
        return [];
      }),
    fetchUsageRecords(workspaceId, {
      start_ms: month.period_start_ms,
      end_ms: month.period_end_ms,
    })
      .then((records) =>
        records.filter((record) => record.agent_id === params.agent_id),
      )
      .catch((error: unknown) => {
        degradedReasons.push(
          messageFromError(error, "Could not load agent usage."),
        );
        return [];
      }),
    listInbox(workspaceId)
      .then((result) => {
        if (result.degraded_reason)
          degradedReasons.push(result.degraded_reason);
        return result.items.filter((item) => item.agent_id === params.agent_id);
      })
      .catch((error: unknown) => {
        degradedReasons.push(
          messageFromError(error, "Could not load agent handoffs."),
        );
        return [];
      }),
    listAgentIncidents(params.agent_id)
      .then((result) => result.items)
      .catch((error: unknown) => {
        degradedReasons.push(
          messageFromError(error, "Could not load agent incidents."),
        );
        return [];
      }),
  ]);

  return (
    <section data-testid="agent-observability-page">
      <ObservatoryScreen
        model={buildObservatoryModel({
          workspaceId,
          traces,
          usage,
          inbox,
          incidents,
          nowMs,
          degradedReason: degradedReasons.join(" ") || undefined,
        })}
        workspaceId={workspaceId}
      />
    </section>
  );
}
