"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  CircleDot,
  Code2,
  Database,
  GitFork,
  ListTree,
  MessageSquare,
  Network,
  PlayCircle,
  Rocket,
  ShieldCheck,
  Wrench,
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
} from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

import {
  evaluateAgentMapEdit,
  INVALID_AGENT_MAP_EDIT,
  type AgentMapData,
  type AgentMapEditResult,
  type AgentMapForkPoint,
  type AgentMapHazard,
  type AgentMapNode,
  type AgentMapNodeKind,
  type AgentMapRisk,
} from "./agent-map-data";

export interface AgentMapProps {
  data: AgentMapData;
}

type MapView = "map" | "list";
type InspectorTab = "evidence" | "coverage" | "code" | "history";

const NODE_KIND_LABEL: Record<AgentMapNodeKind, string> = {
  trigger: "Trigger",
  routine: "Routine",
  policy: "Policy",
  tool: "Tool",
  memory: "Memory",
  eval: "Eval",
  deploy: "Deploy",
  output: "Output",
};

const NODE_KIND_CLASS: Record<AgentMapNodeKind, string> = {
  trigger: "border-info/40 bg-info/5",
  routine: "border-primary/40 bg-primary/5",
  policy: "border-warning/50 bg-warning/5",
  tool: "border-border bg-muted/30",
  memory: "border-success/40 bg-success/5",
  eval: "border-info/40 bg-info/5",
  deploy: "border-warning/50 bg-warning/5",
  output: "border-primary/40 bg-primary/5",
};

const RISK_CLASS: Record<AgentMapRisk, string> = {
  none: "border-border bg-background text-muted-foreground",
  low: "border-info/40 bg-info/5 text-info",
  medium: "border-warning/50 bg-warning/5 text-warning",
  high: "border-destructive/40 bg-destructive/5 text-destructive",
  blocked: "border-destructive bg-destructive/10 text-destructive",
};

function kindIcon(kind: AgentMapNodeKind) {
  if (kind === "trigger")
    return <MessageSquare className="h-4 w-4" aria-hidden />;
  if (kind === "routine") return <Network className="h-4 w-4" aria-hidden />;
  if (kind === "policy") return <ShieldCheck className="h-4 w-4" aria-hidden />;
  if (kind === "tool") return <Wrench className="h-4 w-4" aria-hidden />;
  if (kind === "memory") return <Database className="h-4 w-4" aria-hidden />;
  if (kind === "eval") return <PlayCircle className="h-4 w-4" aria-hidden />;
  if (kind === "deploy") return <Rocket className="h-4 w-4" aria-hidden />;
  if (kind === "output") return <CircleDot className="h-4 w-4" aria-hidden />;
  return <CircleDot className="h-4 w-4" aria-hidden />;
}

function liveBadgeTone(
  state: AgentMapData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function riskLabel(risk: AgentMapRisk): string {
  if (risk === "none") return "No risk";
  if (risk === "blocked") return "Blocked";
  return `${risk[0]?.toUpperCase() ?? ""}${risk.slice(1)} risk`;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 0.01 ? 3 : 2,
    maximumFractionDigits: value < 0.01 ? 3 : 2,
  }).format(value);
}

function MetricCard({
  label,
  value,
  evidence,
}: {
  label: string;
  value: string;
  evidence: string;
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{evidence}</p>
    </div>
  );
}

function EdgeLines({ data }: { data: AgentMapData }) {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full text-border"
      aria-hidden="true"
      data-testid="agent-map-edges"
    >
      {data.edges.map((edge) => {
        const source = data.nodes.find((node) => node.id === edge.source);
        const target = data.nodes.find((node) => node.id === edge.target);
        if (!source || !target) return null;
        return (
          <g key={edge.id}>
            <line
              x1={`${source.x}%`}
              y1={`${source.y}%`}
              x2={`${target.x}%`}
              y2={`${target.y}%`}
              stroke="currentColor"
              strokeWidth={edge.status === "blocked" ? 3 : 2}
              strokeDasharray={edge.status === "ok" ? undefined : "7 5"}
            />
            <text
              x={`${(source.x + target.x) / 2}%`}
              y={`${(source.y + target.y) / 2}%`}
              className="fill-muted-foreground text-[10px]"
              textAnchor="middle"
            >
              {edge.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function MapNodeButton({
  node,
  selected,
  onSelect,
}: {
  node: AgentMapNode;
  selected: boolean;
  onSelect: (nodeId: string) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      aria-label={`${NODE_KIND_LABEL[node.kind]} ${node.label}. ${riskLabel(
        node.risk,
      )}. ${node.coveragePercent}% eval coverage.`}
      className={cn(
        "absolute flex w-44 -translate-x-1/2 -translate-y-1/2 flex-col gap-2 rounded-md border p-3 text-left text-sm shadow-sm transition-colors duration-swift ease-standard hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
        NODE_KIND_CLASS[node.kind],
        selected ? "ring-2 ring-primary/60" : "",
      )}
      style={{ left: `${node.x}%`, top: `${node.y}%` }}
      onClick={() => onSelect(node.id)}
      data-testid={`agent-map-node-${node.id}`}
    >
      <span className="flex items-center gap-2">
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background">
          {kindIcon(node.kind)}
        </span>
        <span className="min-w-0">
          <span className="block break-words font-semibold leading-snug">
            {node.label}
          </span>
          <span className="text-xs text-muted-foreground">
            {NODE_KIND_LABEL[node.kind]}
          </span>
        </span>
      </span>
      <span className="flex flex-wrap gap-1 text-xs">
        <span className="rounded-md bg-background px-2 py-0.5 text-muted-foreground">
          {node.dependencies.length} deps
        </span>
        <span className="rounded-md bg-background px-2 py-0.5 text-muted-foreground">
          {node.coveragePercent}% eval
        </span>
        <span
          className={cn(
            "rounded-md border px-2 py-0.5 font-medium",
            RISK_CLASS[node.risk],
          )}
        >
          {riskLabel(node.risk)}
        </span>
      </span>
    </button>
  );
}

function AgentMapCanvas({
  data,
  selectedNodeId,
  onSelectNode,
}: {
  data: AgentMapData;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}) {
  if (data.nodes.length === 0) {
    return (
      <StatePanel state="empty" title="No map instrumentation yet">
        <p>
          Run a preview or replay a production turn to generate dependency,
          tool, memory, and eval coverage.
        </p>
      </StatePanel>
    );
  }

  return (
    <section
      className="rounded-md border bg-card p-3"
      aria-labelledby="agent-map-canvas-heading"
      data-testid="agent-map-canvas"
    >
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold" id="agent-map-canvas-heading">
            Comprehension map
          </h3>
          <p className="text-sm text-muted-foreground">
            Instrumentation view of dependencies, tool grants, memory writes,
            eval coverage, and deploy impact.
          </p>
        </div>
        <span className="rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground">
          Logic source remains behavior, tools, memory, evals, and code/config.
        </span>
      </div>
      <div className="overflow-auto rounded-md border bg-background">
        <div className="relative min-h-[34rem] min-w-[54rem]">
          <EdgeLines data={data} />
          {data.nodes.map((node) => (
            <MapNodeButton
              key={node.id}
              node={node}
              selected={selectedNodeId === node.id}
              onSelect={onSelectNode}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function AgentMapListView({
  data,
  selectedNodeId,
  onSelectNode,
}: {
  data: AgentMapData;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}) {
  if (data.nodes.length === 0) {
    return (
      <StatePanel state="empty" title="No list view rows yet">
        <p>The list view will use the same source as the visual map.</p>
      </StatePanel>
    );
  }

  return (
    <section
      className="rounded-md border bg-card p-3"
      aria-labelledby="agent-map-list-heading"
      data-testid="agent-map-list-view"
    >
      <div className="mb-3 flex items-center gap-2">
        <ListTree className="h-4 w-4" aria-hidden />
        <h3 className="text-sm font-semibold" id="agent-map-list-heading">
          Accessible list view
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[42rem] text-left text-sm">
          <thead className="text-xs text-muted-foreground">
            <tr className="border-b">
              <th className="py-2 pr-3 font-medium">Object</th>
              <th className="py-2 pr-3 font-medium">Dependencies</th>
              <th className="py-2 pr-3 font-medium">Evidence</th>
              <th className="py-2 pr-3 font-medium">Risk</th>
              <th className="py-2 pr-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.nodes.map((node) => (
              <tr
                key={node.id}
                className={cn(
                  "border-b last:border-0",
                  selectedNodeId === node.id ? "bg-primary/5" : "",
                )}
              >
                <td className="py-3 pr-3">
                  <p className="font-medium">{node.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {NODE_KIND_LABEL[node.kind]} · {node.codeRef}
                  </p>
                </td>
                <td className="py-3 pr-3 text-muted-foreground">
                  {node.dependencies.length > 0
                    ? node.dependencies.join(", ")
                    : "None"}
                </td>
                <td className="py-3 pr-3 text-muted-foreground">
                  {node.evidence.join(", ")}
                </td>
                <td className="py-3 pr-3">
                  <span
                    className={cn(
                      "inline-flex rounded-md border px-2 py-1 text-xs font-medium",
                      RISK_CLASS[node.risk],
                    )}
                  >
                    {riskLabel(node.risk)}
                  </span>
                </td>
                <td className="py-3 pr-3">
                  <button
                    type="button"
                    className="rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    onClick={() => onSelectNode(node.id)}
                    data-testid={`agent-map-list-inspect-${node.id}`}
                  >
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function InspectorTabs({
  tab,
  onTabChange,
}: {
  tab: InspectorTab;
  onTabChange: (tab: InspectorTab) => void;
}) {
  const tabs: { id: InspectorTab; label: string }[] = [
    { id: "evidence", label: "Evidence" },
    { id: "coverage", label: "Coverage" },
    { id: "code", label: "Code/config" },
    { id: "history", label: "History" },
  ];
  return (
    <div
      className="grid gap-1 [grid-template-columns:repeat(auto-fit,minmax(min(100%,7rem),1fr))]"
      role="tablist"
      aria-label="Map inspector tabs"
    >
      {tabs.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={tab === item.id}
          className={cn(
            "rounded-md border px-2 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
            tab === item.id
              ? "bg-primary text-primary-foreground"
              : "bg-background",
          )}
          onClick={() => onTabChange(item.id)}
          data-testid={`agent-map-inspector-tab-${item.id}`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function InspectorBody({
  node,
  tab,
  hazards,
}: {
  node: AgentMapNode;
  tab: InspectorTab;
  hazards: AgentMapHazard[];
}) {
  if (tab === "coverage") {
    return (
      <div className="space-y-4" data-testid="agent-map-inspector-coverage">
        <ConfidenceMeter
          value={node.coveragePercent}
          label="Eval coverage"
          evidence={`Evidence: ${node.evalIds.join(", ") || "No eval linked"}`}
        />
        <dl className="grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,8rem),1fr))]">
          <div>
            <dt className="text-muted-foreground">Latency</dt>
            <dd className="font-medium tabular-nums">{node.latencyMs} ms</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Cost</dt>
            <dd className="font-medium tabular-nums">
              {formatUsd(node.costUsd)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Tools</dt>
            <dd>{node.toolIds.join(", ") || "None"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Memory</dt>
            <dd>{node.memoryIds.join(", ") || "None"}</dd>
          </div>
        </dl>
      </div>
    );
  }

  if (tab === "code") {
    return (
      <div className="space-y-3" data-testid="agent-map-inspector-code">
        <div className="rounded-md border bg-background p-3">
          <p className="flex items-center gap-2 text-sm font-medium">
            <Code2 className="h-4 w-4" aria-hidden />
            Canonical source
          </p>
          <code className="mt-2 block break-all text-xs text-muted-foreground">
            {node.codeRef}
          </code>
        </div>
        <p className="text-sm text-muted-foreground">
          The map explains this object. The source representation remains
          reviewable in code/config and structured agent surfaces.
        </p>
      </div>
    );
  }

  if (tab === "history") {
    return (
      <div className="space-y-2" data-testid="agent-map-inspector-history">
        <p className="rounded-md border bg-background p-3 text-sm">
          Last change: {node.objectState} object inspected from branch history.
        </p>
        {node.readonlyReason ? (
          <p className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
            {node.readonlyReason}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="agent-map-inspector-evidence">
      <ul className="space-y-2">
        {node.evidence.map((evidence) => (
          <li
            key={evidence}
            className="rounded-md border bg-background p-3 text-sm"
          >
            {evidence}
          </li>
        ))}
      </ul>
      {hazards.length > 0 ? (
        <div className="space-y-2">
          {hazards.map((hazard) => (
            <RiskHalo
              key={hazard.id}
              level={hazard.severity}
              label={`${hazard.title}: ${riskLabel(hazard.severity)}`}
            >
              <div className="rounded-md bg-background p-3 text-sm">
                <p className="font-medium">{hazard.title}</p>
                <p className="mt-1 text-muted-foreground">
                  {hazard.description}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Evidence: {hazard.evidence}
                </p>
              </div>
            </RiskHalo>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function InspectorPanel({
  data,
  node,
  forkNotice,
  onFork,
}: {
  data: AgentMapData;
  node: AgentMapNode | null;
  forkNotice: string | null;
  onFork: (fork: AgentMapForkPoint) => void;
}) {
  const [tab, setTab] = useState<InspectorTab>("evidence");
  if (!node) {
    return (
      <StatePanel state="empty" title="No object selected">
        <p>Select a map object or list row to inspect evidence and controls.</p>
      </StatePanel>
    );
  }
  const hazards = data.hazards.filter((hazard) =>
    hazard.nodeIds.includes(node.id),
  );
  const fork = data.forkPoints.find(
    (candidate) => candidate.nodeId === node.id,
  );
  const stateTreatment = OBJECT_STATE_TREATMENTS[node.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[node.trust];

  return (
    <aside
      className="rounded-md border bg-card p-4"
      aria-labelledby="agent-map-inspector-heading"
      data-testid="agent-map-inspector"
    >
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Inspector
          </p>
          <h3
            className="mt-1 text-lg font-semibold"
            id="agent-map-inspector-heading"
          >
            {node.label}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">{node.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span
            className={cn(
              "inline-flex rounded-md border px-2 py-1 text-xs font-medium",
              stateTreatment.className,
            )}
          >
            {stateTreatment.label}
          </span>
          <span
            className={cn(
              "inline-flex rounded-md border px-2 py-1 text-xs font-medium",
              trustTreatment.className,
            )}
          >
            {trustTreatment.label}
          </span>
          <span
            className={cn(
              "inline-flex rounded-md border px-2 py-1 text-xs font-medium",
              RISK_CLASS[node.risk],
            )}
          >
            {riskLabel(node.risk)}
          </span>
        </div>
        <InspectorTabs tab={tab} onTabChange={setTab} />
        <InspectorBody node={node} tab={tab} hazards={hazards} />
        {fork ? (
          <div className="rounded-md border bg-background p-3">
            <p className="text-sm font-medium">{fork.label}</p>
            <dl className="mt-2 grid gap-2 text-xs text-muted-foreground [grid-template-columns:repeat(auto-fit,minmax(min(100%,8rem),1fr))]">
              <div>
                <dt>Tokens</dt>
                <dd>{fork.tokenDelta}</dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd>{fork.latencyDelta}</dd>
              </div>
              <div>
                <dt>Cost</dt>
                <dd>{fork.costDelta}</dd>
              </div>
              <div>
                <dt>Eval</dt>
                <dd>{fork.evalDelta}</dd>
              </div>
            </dl>
            <button
              type="button"
              className="mt-3 inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              onClick={() => onFork(fork)}
              data-testid="agent-map-fork"
            >
              <GitFork className="h-4 w-4" aria-hidden />
              Fork from here
            </button>
          </div>
        ) : (
          <p className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
            Fork from here is unavailable for this object because no trace
            snapshot is attached.
          </p>
        )}
        {forkNotice ? (
          <p
            className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
            aria-live="polite"
            data-testid="agent-map-fork-notice"
          >
            {forkNotice}
          </p>
        ) : null}
      </div>
    </aside>
  );
}

function HazardPanel({
  data,
  editResult,
  onInvalidEdit,
}: {
  data: AgentMapData;
  editResult: AgentMapEditResult | null;
  onInvalidEdit: () => void;
}) {
  return (
    <section
      className="rounded-md border bg-card p-4"
      aria-labelledby="agent-map-hazards-heading"
      data-testid="agent-map-hazards"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            Hazards
          </p>
          <h3
            className="mt-1 text-sm font-semibold"
            id="agent-map-hazards-heading"
          >
            Invalid edits are rejected before preview.
          </h3>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          onClick={onInvalidEdit}
          disabled={data.nodes.length === 0}
          data-testid="agent-map-invalid-edit"
        >
          Test invalid attach
        </button>
      </div>
      <div className="mt-3 grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr))]">
        {data.hazards.map((hazard) => (
          <RiskHalo
            key={hazard.id}
            level={hazard.severity}
            label={`${hazard.title}: ${riskLabel(hazard.severity)}`}
          >
            <div className="rounded-md bg-background p-3 text-sm">
              <p className="font-medium">{hazard.title}</p>
              <p className="mt-1 text-muted-foreground">
                {hazard.requiredBehavior}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Evidence: {hazard.evidence}
              </p>
            </div>
          </RiskHalo>
        ))}
      </div>
      {editResult ? (
        <p
          className={cn(
            "mt-3 rounded-md border px-3 py-2 text-sm",
            editResult.accepted
              ? "border-success/40 bg-success/5 text-success"
              : "border-destructive/40 bg-destructive/5 text-muted-foreground",
          )}
          role="alert"
          data-testid="agent-map-edit-result"
        >
          {editResult.reason} Evidence: {editResult.evidence}
        </p>
      ) : null}
    </section>
  );
}

function SourceParityPanel({ data }: { data: AgentMapData }) {
  return (
    <EvidenceCallout
      title="Map is a lens, not the source of logic"
      source={`${data.branch}; agent.behavior.yaml; tools.yaml; memory.policy.yaml; evals/refunds.yaml`}
      confidence={data.coverage.dependency}
      confidenceLevel={data.confidence}
      tone="info"
    >
      <p>
        A builder can inspect the same behavior through the profile, behavior
        editor, tools, memory, evals, and code/config without opening this map.
      </p>
    </EvidenceCallout>
  );
}

export function AgentMap({ data }: AgentMapProps) {
  const [view, setView] = useState<MapView>("map");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    data.nodes[0]?.id ?? null,
  );
  const [editResult, setEditResult] = useState<AgentMapEditResult | null>(null);
  const [forkNotice, setForkNotice] = useState<string | null>(null);
  const selectedNode = useMemo(
    () =>
      data.nodes.find((node) => node.id === selectedNodeId) ??
      data.nodes[0] ??
      null,
    [data.nodes, selectedNodeId],
  );
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];

  function selectNode(nodeId: string) {
    setSelectedNodeId(nodeId);
    setForkNotice(null);
  }

  function testInvalidEdit() {
    setEditResult(evaluateAgentMapEdit(data, INVALID_AGENT_MAP_EDIT));
  }

  function forkFromHere(fork: AgentMapForkPoint) {
    setForkNotice(
      `Fork preview staged on ${fork.branch}. Evidence: ${fork.evidence}.`,
    );
  }

  return (
    <div className="flex flex-col gap-6" data-testid="agent-map">
      <section className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]">
        <div className="rounded-md border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Agent map
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="text-2xl font-semibold tracking-tight">
              {data.agentName}
            </h2>
            <LiveBadge tone={liveBadgeTone(data.objectState)}>
              {objectTreatment.label}
            </LiveBadge>
            <span
              className={cn(
                "inline-flex h-7 items-center rounded-md border px-2.5 text-xs font-medium",
                trustTreatment.className,
              )}
            >
              {trustTreatment.label}
            </span>
          </div>
          <p className="mt-3 max-w-3xl text-sm text-muted-foreground">
            Comprehension-first instrumentation for dependencies, tools, memory,
            eval coverage, hazards, and forkable trace state.
          </p>
          <dl className="mt-4 grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,10rem),1fr))]">
            <div>
              <dt className="text-muted-foreground">Branch</dt>
              <dd className="break-words font-medium">{data.branch}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">State</dt>
              <dd className="font-medium">{objectTreatment.label}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Agent</dt>
              <dd className="break-all font-medium">{data.agentId}</dd>
            </div>
          </dl>
        </div>
        <SourceParityPanel data={data} />
      </section>

      {data.degradedReason ? (
        <StatePanel state="degraded" title="Map data is degraded">
          <p>{data.degradedReason}</p>
        </StatePanel>
      ) : null}

      <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
        <MetricCard
          label="Dependency coverage"
          value={`${data.coverage.dependency}%`}
          evidence="Traces plus map edge validation"
        />
        <MetricCard
          label="Tool coverage"
          value={`${data.coverage.tool}%`}
          evidence="Tool grants and safety contracts"
        />
        <MetricCard
          label="Memory coverage"
          value={`${data.coverage.memory}%`}
          evidence="Memory policy and write audit"
        />
        <MetricCard
          label="Eval coverage"
          value={`${data.coverage.eval}%`}
          evidence="Replay and parity evals"
        />
      </section>

      <div
        className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,8rem),1fr))]"
        role="tablist"
        aria-label="Map display modes"
      >
        <button
          type="button"
          role="tab"
          aria-selected={view === "map"}
          className={cn(
            "inline-flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
            view === "map"
              ? "bg-primary text-primary-foreground"
              : "bg-background",
          )}
          onClick={() => setView("map")}
          data-testid="agent-map-view-map"
        >
          <Network className="h-4 w-4" aria-hidden />
          Map
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === "list"}
          className={cn(
            "inline-flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
            view === "list"
              ? "bg-primary text-primary-foreground"
              : "bg-background",
          )}
          onClick={() => setView("list")}
          data-testid="agent-map-view-list"
        >
          <ListTree className="h-4 w-4" aria-hidden />
          List
        </button>
      </div>

      <section className="grid gap-4">
        <div className="space-y-4">
          {view === "map" ? (
            <AgentMapCanvas
              data={data}
              selectedNodeId={selectedNode?.id ?? null}
              onSelectNode={selectNode}
            />
          ) : (
            <AgentMapListView
              data={data}
              selectedNodeId={selectedNode?.id ?? null}
              onSelectNode={selectNode}
            />
          )}
          <HazardPanel
            data={data}
            editResult={editResult}
            onInvalidEdit={testInvalidEdit}
          />
        </div>
        <InspectorPanel
          data={data}
          node={selectedNode}
          forkNotice={forkNotice}
          onFork={forkFromHere}
        />
      </section>
    </div>
  );
}
