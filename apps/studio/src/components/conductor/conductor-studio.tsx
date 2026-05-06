"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeDollarSign,
  GitBranch,
  Handshake,
  Network,
  ShieldCheck,
  Timer,
  UsersRound,
} from "lucide-react";

import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
  RiskHalo,
  StatePanel,
} from "@/components/target";
import {
  OBJECT_STATE_TREATMENTS,
  TRUST_STATE_TREATMENTS,
  type ConfidenceLevel,
} from "@/lib/design-tokens";
import type {
  ConductorAgentStatus,
  ConductorData,
  ConductorSubAgent,
  HandoffContract,
  HandoffState,
} from "@/lib/conductor";
import { cn } from "@/lib/utils";

export interface ConductorStudioProps {
  data: ConductorData;
}

const STATUS_CLASS: Record<ConductorAgentStatus, string> = {
  ready: "border-info/40 bg-info/5 text-info",
  active: "border-success/40 bg-success/5 text-success",
  degraded: "border-warning/50 bg-warning/5 text-warning",
  blocked: "border-destructive/40 bg-destructive/5 text-destructive",
};

const CONTRACT_CLASS: Record<HandoffState, string> = {
  ready: "border-info/40 bg-info/5 text-info",
  active: "border-success/40 bg-success/5 text-success",
  violated: "border-warning/50 bg-warning/5 text-warning",
  blocked: "border-destructive/40 bg-destructive/5 text-destructive",
};

function liveBadgeTone(
  state: ConductorData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function riskLevel(state: HandoffState): "none" | "low" | "medium" | "blocked" {
  if (state === "violated") return "medium";
  if (state === "blocked") return "blocked";
  if (state === "ready") return "low";
  return "none";
}

function confidenceValue(level: ConfidenceLevel): number {
  if (level === "high") return 95;
  if (level === "medium") return 76;
  if (level === "low") return 52;
  return 0;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 0.01 ? 3 : 2,
    maximumFractionDigits: value < 0.01 ? 3 : 2,
  }).format(value);
}

function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-2 text-xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function SubAgentAssets({
  agents,
  selectedId,
  onSelect,
}: {
  agents: ConductorSubAgent[];
  selectedId: string | null;
  onSelect: (agentId: string) => void;
}) {
  if (agents.length === 0) {
    return (
      <StatePanel state="empty" title="No sub-agents attached">
        <p>Add a reviewed sub-agent asset before creating handoff contracts.</p>
      </StatePanel>
    );
  }

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="conductor-assets-heading"
      data-testid="conductor-assets"
    >
      <div className="mb-3 flex items-center gap-2">
        <UsersRound className="h-4 w-4" aria-hidden />
        <h3 className="text-sm font-semibold" id="conductor-assets-heading">
          Sub-agent assets
        </h3>
      </div>
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr))]">
        {agents.map((agent) => (
          <button
            key={agent.id}
            type="button"
            aria-pressed={selectedId === agent.id}
            className={cn(
              "min-w-0 rounded-md border bg-background p-3 text-left text-sm transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              selectedId === agent.id
                ? "border-primary ring-1 ring-primary/50"
                : "",
            )}
            onClick={() => onSelect(agent.id)}
            data-testid={`conductor-agent-${agent.id}`}
          >
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{agent.name}</span>
              <span
                className={cn(
                  "rounded-md border px-2 py-0.5 text-xs font-medium",
                  STATUS_CLASS[agent.status],
                )}
              >
                {agent.status}
              </span>
              <span className="rounded-md border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {agent.version}
              </span>
            </span>
            <span className="mt-2 block text-muted-foreground">
              {agent.purpose}
            </span>
            <span className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>Owner: {agent.owner}</span>
              <span>Current: {agent.currentOwner}</span>
              <span>{agent.evalCoveragePercent}% eval</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function Topology({
  data,
  selectedAgentId,
}: {
  data: ConductorData;
  selectedAgentId: string | null;
}) {
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="conductor-topology-heading"
      data-testid="conductor-topology"
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4" aria-hidden />
          <h3 className="text-sm font-semibold" id="conductor-topology-heading">
            Conductor topology
          </h3>
        </div>
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))]">
          {data.subAgents.map((agent) => (
            <div
              key={agent.id}
              className={cn(
                "rounded-md border bg-background p-3",
                selectedAgentId === agent.id ? "ring-2 ring-primary/50" : "",
              )}
            >
              <p className="font-semibold">{agent.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {agent.activeHandoffs} active handoffs · {agent.memoryAccess}
              </p>
            </div>
          ))}
        </div>
        <div className="space-y-2" aria-label="Visible handoff edges">
          {data.topology.map((edge) => {
            const source = data.subAgents.find(
              (agent) => agent.id === edge.source,
            );
            const target = data.subAgents.find(
              (agent) => agent.id === edge.target,
            );
            return (
              <div
                key={edge.id}
                className="flex flex-col gap-2 rounded-md border bg-background p-3 text-sm sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="min-w-0 break-words">
                  {source?.name ?? edge.source} to {target?.name ?? edge.target}
                </span>
                <span
                  className={cn(
                    "w-fit rounded-md border px-2 py-0.5 text-xs font-medium",
                    CONTRACT_CLASS[edge.state],
                  )}
                >
                  {edge.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function HandoffContracts({
  contracts,
  selectedId,
  onSelect,
}: {
  contracts: HandoffContract[];
  selectedId: string | null;
  onSelect: (contractId: string) => void;
}) {
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="conductor-contracts-heading"
      data-testid="conductor-contracts"
    >
      <div className="mb-3 flex items-center gap-2">
        <Handshake className="h-4 w-4" aria-hidden />
        <h3 className="text-sm font-semibold" id="conductor-contracts-heading">
          Handoff contracts
        </h3>
      </div>
      <div className="space-y-3">
        {contracts.map((contract) => (
          <RiskHalo
            key={contract.id}
            level={riskLevel(contract.state)}
            label={`${contract.name} contract state: ${contract.state}`}
          >
            <button
              type="button"
              aria-pressed={selectedId === contract.id}
              className={cn(
                "w-full rounded-md bg-background p-3 text-left text-sm hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                selectedId === contract.id ? "ring-1 ring-primary/50" : "",
              )}
              onClick={() => onSelect(contract.id)}
              data-testid={`conductor-contract-${contract.id}`}
            >
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{contract.name}</span>
                <span
                  className={cn(
                    "rounded-md border px-2 py-0.5 text-xs font-medium",
                    CONTRACT_CLASS[contract.state],
                  )}
                >
                  {contract.state}
                </span>
              </span>
              <span className="mt-2 block text-muted-foreground">
                {contract.from} to {contract.to} · timeout {contract.timeoutMs}{" "}
                ms · budget {formatUsd(contract.budgetUsd)}
              </span>
              {contract.violation ? (
                <span className="mt-2 block text-warning">
                  {contract.violation}
                </span>
              ) : null}
            </button>
          </RiskHalo>
        ))}
      </div>
    </section>
  );
}

function ContractDetail({ contract }: { contract: HandoffContract | null }) {
  if (!contract) {
    return (
      <StatePanel state="empty" title="No contract selected">
        <p>
          Select a handoff contract to inspect schemas, timeout, grants, and
          fallback.
        </p>
      </StatePanel>
    );
  }

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="conductor-contract-detail"
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Contract detail
          </p>
          <h3 className="mt-1 text-lg font-semibold">{contract.name}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {contract.purpose}
          </p>
        </div>
        {contract.violation ? (
          <StatePanel state="stale" title="Contract violation">
            <p>{contract.violation}</p>
          </StatePanel>
        ) : null}
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Input schema
            </p>
            <p className="mt-1 break-words text-sm">
              {contract.inputSchema.join(", ")}
            </p>
          </div>
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Output schema
            </p>
            <p className="mt-1 break-words text-sm">
              {contract.outputSchema.join(", ")}
            </p>
          </div>
        </div>
        <dl className="grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
          <div className="rounded-md border bg-background p-3">
            <dt className="text-xs text-muted-foreground">Fallback</dt>
            <dd className="mt-1">{contract.fallback}</dd>
          </div>
          <div className="rounded-md border bg-background p-3">
            <dt className="text-xs text-muted-foreground">Memory access</dt>
            <dd className="mt-1">{contract.memoryAccess}</dd>
          </div>
          <div className="rounded-md border bg-background p-3">
            <dt className="text-xs text-muted-foreground">Tool grants</dt>
            <dd className="mt-1">{contract.toolGrants.join("; ")}</dd>
          </div>
          <div className="rounded-md border bg-background p-3">
            <dt className="text-xs text-muted-foreground">Current owner</dt>
            <dd className="mt-1">{contract.currentOwner}</dd>
          </div>
        </dl>
        <EvidenceCallout
          title="Contract evidence"
          source={contract.evidenceTrace}
          tone={contract.state === "violated" ? "warning" : "info"}
        >
          Violating a handoff contract is explicit, linked to a trace, and
          routes to the configured fallback before customer output resumes.
        </EvidenceCallout>
      </div>
    </section>
  );
}

function AgentInspector({ agent }: { agent: ConductorSubAgent | null }) {
  if (!agent) {
    return (
      <StatePanel state="empty" title="No sub-agent selected">
        <p>
          Select a sub-agent to inspect tools, budgets, owners, failures, and
          trace spans.
        </p>
      </StatePanel>
    );
  }
  const stateTreatment = OBJECT_STATE_TREATMENTS[agent.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[agent.trust];
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="conductor-inspector-heading"
      data-testid="conductor-inspector"
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Sub-agent inspector
          </p>
          <h3
            className="mt-1 text-lg font-semibold"
            id="conductor-inspector-heading"
          >
            {agent.name}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">{agent.purpose}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span
            className={cn(
              "rounded-md border px-2 py-1 text-xs font-medium",
              stateTreatment.className,
            )}
          >
            {stateTreatment.label}
          </span>
          <span
            className={cn(
              "rounded-md border px-2 py-1 text-xs font-medium",
              trustTreatment.className,
            )}
          >
            {trustTreatment.label}
          </span>
          <span
            className={cn(
              "rounded-md border px-2 py-1 text-xs font-medium",
              STATUS_CLASS[agent.status],
            )}
          >
            {agent.status}
          </span>
        </div>
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,10rem),1fr))]">
          <Metric
            label="Budget"
            value={`${formatUsd(agent.spentUsd)} / ${formatUsd(agent.budgetUsd)}`}
            detail={agent.costEvidence}
            icon={<BadgeDollarSign className="h-4 w-4" aria-hidden />}
          />
          <Metric
            label="Latency"
            value={`${agent.latencyP95Ms} ms`}
            detail={agent.latencyEvidence}
            icon={<Timer className="h-4 w-4" aria-hidden />}
          />
        </div>
        <ConfidenceMeter
          value={confidenceValue(agent.evalConfidence)}
          level={agent.evalConfidence}
          label="Eval coverage"
          evidence={`${agent.evalCoveragePercent}% of handoff cases covered for ${agent.name}`}
        />
        <section className="rounded-md border bg-background p-3">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4" aria-hidden />
            Tools and memory
          </p>
          <div className="mt-2 space-y-2 text-sm text-muted-foreground">
            <p>{agent.memoryAccess}</p>
            {agent.tools.length > 0 ? (
              agent.tools.map((tool) => (
                <p key={tool.name}>
                  {tool.name}: {tool.mode} · {tool.evidence}
                </p>
              ))
            ) : (
              <p>No tool grants for this sub-agent.</p>
            )}
          </div>
        </section>
        <section
          className="rounded-md border bg-background p-3"
          data-testid="conductor-failure"
        >
          <p className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            Failure paths
          </p>
          <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
            {agent.failurePaths.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}

function DelegationTrace({ data }: { data: ConductorData }) {
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="conductor-delegation-heading"
      data-testid="conductor-delegation"
    >
      <div className="mb-3 flex items-center gap-2">
        <GitBranch className="h-4 w-4" aria-hidden />
        <h3 className="text-sm font-semibold" id="conductor-delegation-heading">
          Traceable delegation
        </h3>
      </div>
      <div className="space-y-3">
        {data.delegations.map((delegation) => (
          <div
            key={delegation.id}
            className="rounded-md border bg-background p-3 text-sm"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="font-semibold">
                {delegation.sourceAgent} to {delegation.targetAgent}
              </p>
              <span
                className={cn(
                  "w-fit rounded-md border px-2 py-0.5 text-xs font-medium",
                  delegation.status === "ok"
                    ? "border-success/40 bg-success/5 text-success"
                    : delegation.status === "warning"
                      ? "border-warning/50 bg-warning/5 text-warning"
                      : "border-destructive/40 bg-destructive/5 text-destructive",
                )}
              >
                {delegation.status}
              </span>
            </div>
            <p className="mt-2 text-muted-foreground">
              {delegation.traceId}#{delegation.spanId} · {delegation.latencyMs}{" "}
              ms · {formatUsd(delegation.costUsd)}
            </p>
            <p className="mt-1 text-muted-foreground">{delegation.evidence}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ConductorStudio({ data }: ConductorStudioProps) {
  const [selectedAgentId, setSelectedAgentId] = useState(
    data.subAgents[0]?.id ?? null,
  );
  const [selectedContractId, setSelectedContractId] = useState(
    data.contracts[0]?.id ?? null,
  );
  const selectedAgent = useMemo(
    () =>
      data.subAgents.find((agent) => agent.id === selectedAgentId) ??
      data.subAgents[0] ??
      null,
    [data.subAgents, selectedAgentId],
  );
  const selectedContract = useMemo(
    () =>
      data.contracts.find((contract) => contract.id === selectedContractId) ??
      data.contracts[0] ??
      null,
    [data.contracts, selectedContractId],
  );
  const activeContracts = data.contracts.filter(
    (contract) => contract.state === "active",
  ).length;
  const failureCount = data.contracts.filter(
    (contract) => contract.state === "violated" || contract.state === "blocked",
  ).length;
  const totalBudget = data.subAgents.reduce(
    (sum, agent) => sum + agent.budgetUsd,
    0,
  );
  const p95Latency =
    data.subAgents.length > 0
      ? Math.max(...data.subAgents.map((agent) => agent.latencyP95Ms))
      : 0;

  return (
    <main
      className="flex min-w-0 flex-col gap-6"
      data-testid="conductor-studio"
    >
      <section className="rounded-md border bg-card p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Multi-agent conductor
            </p>
            <h2 className="mt-2 break-words text-2xl font-semibold">
              {data.agentName}
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Inspect sub-agent purpose, tools, budgets, handoff contracts,
              ownership, failure paths, and traceable delegation without hidden
              orchestration.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <LiveBadge tone={liveBadgeTone(data.objectState)}>
              {OBJECT_STATE_TREATMENTS[data.objectState].label}
            </LiveBadge>
            <LiveBadge tone={data.trust === "blocked" ? "paused" : "staged"}>
              {TRUST_STATE_TREATMENTS[data.trust].label}
            </LiveBadge>
          </div>
        </div>
        {data.degradedReason ? (
          <StatePanel
            state={data.permissionReason ? "permission" : "degraded"}
            title={
              data.permissionReason
                ? "Conductor editing locked"
                : "Conductor data degraded"
            }
            className="mt-4"
            action={
              data.permissionReason ? (
                <button
                  type="button"
                  disabled
                  className="rounded-md border bg-background px-3 py-2 text-sm text-muted-foreground"
                  data-testid="conductor-request-approval"
                >
                  Request orchestration approval
                </button>
              ) : null
            }
          >
            <p>{data.permissionReason ?? data.degradedReason}</p>
          </StatePanel>
        ) : null}
      </section>

      <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr))]">
        <Metric
          label="Sub-agents"
          value={data.subAgents.length.toString()}
          detail="Assets with purpose, owner, version, tools, budget, trace spans"
          icon={<UsersRound className="h-4 w-4" aria-hidden />}
        />
        <Metric
          label="Active handoffs"
          value={activeContracts.toString()}
          detail={`${failureCount} explicit failure or blocked paths visible`}
          icon={<Handshake className="h-4 w-4" aria-hidden />}
        />
        <Metric
          label="Budget envelope"
          value={formatUsd(totalBudget)}
          detail="Per-turn budget across selected sub-agent assets"
          icon={<BadgeDollarSign className="h-4 w-4" aria-hidden />}
        />
        <Metric
          label="Latency by agent"
          value={`${p95Latency} ms`}
          detail="Worst p95 among active sub-agent spans"
          icon={<Timer className="h-4 w-4" aria-hidden />}
        />
      </section>

      <div className="grid min-w-0 gap-6">
        <div className="min-w-0 space-y-6">
          <Topology data={data} selectedAgentId={selectedAgent?.id ?? null} />
          <SubAgentAssets
            agents={data.subAgents}
            selectedId={selectedAgent?.id ?? null}
            onSelect={setSelectedAgentId}
          />
          <HandoffContracts
            contracts={data.contracts}
            selectedId={selectedContract?.id ?? null}
            onSelect={setSelectedContractId}
          />
          <DelegationTrace data={data} />
        </div>
        <aside className="min-w-0 space-y-6">
          <AgentInspector agent={selectedAgent} />
          <ContractDetail contract={selectedContract} />
          <EvidenceCallout
            title="No hidden orchestration"
            source={data.orchestrationEvidence}
            confidence={92}
            confidenceLevel="high"
            tone="success"
          >
            Each delegation names the source agent, target agent, contract,
            current owner, span evidence, budget, latency, fallback, and
            memory/tool grants before a composed answer can proceed.
          </EvidenceCallout>
        </aside>
      </div>
    </main>
  );
}
