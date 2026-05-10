"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Braces,
  ClipboardList,
  KeyRound,
  PlayCircle,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import { InstantToolImport } from "@/components/tools/instant-tool-import";
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
import {
  type ToolSideEffect,
  type ToolsRoomData,
  type ToolsRoomTool,
} from "@/lib/agent-tools";
import { promoteToolContract, type ToolContract } from "@/lib/tool-contracts";
import { cn } from "@/lib/utils";

export interface ToolsRoomProps {
  data: ToolsRoomData;
}

const SIDE_EFFECT_CLASS: Record<ToolSideEffect, string> = {
  read: "border-info/40 bg-info/5 text-info",
  write: "border-warning/50 bg-warning/5 text-warning",
  "money-movement": "border-destructive/40 bg-destructive/5 text-destructive",
  "external-message": "border-warning/50 bg-warning/5 text-warning",
};

function liveBadgeTone(
  state: ToolsRoomData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toISOString().replace("T", " ").slice(0, 16);
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function Catalog({
  tools,
  selectedId,
  onSelect,
}: {
  tools: ToolsRoomTool[];
  selectedId: string | null;
  onSelect: (toolId: string) => void;
}) {
  if (tools.length === 0) {
    return (
      <StatePanel state="empty" title="No tools bound yet">
        <p>
          Paste a curl command, OpenAPI fragment, or Postman sample to draft a
          typed tool with schema, auth, mock, and eval coverage.
        </p>
      </StatePanel>
    );
  }

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-3"
      aria-labelledby="tools-catalog-heading"
      data-testid="tools-room-catalog"
    >
      <div className="mb-3 flex items-center gap-2">
        <Wrench className="h-4 w-4" aria-hidden />
        <h3 className="text-sm font-semibold" id="tools-catalog-heading">
          Catalog
        </h3>
      </div>
      <div className="space-y-2">
        {tools.map((tool) => (
          <button
            key={tool.id}
            type="button"
            className={cn(
              "w-full rounded-md border bg-background p-3 text-left text-sm transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              selectedId === tool.id
                ? "border-primary ring-1 ring-primary/50"
                : "",
            )}
            onClick={() => onSelect(tool.id)}
            aria-pressed={selectedId === tool.id}
            data-testid={`tools-room-catalog-${tool.id}`}
          >
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{tool.name}</span>
              <span className="rounded-md border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {tool.kind}
              </span>
              <span
                className={cn(
                  "rounded-md border px-2 py-0.5 text-xs font-medium",
                  SIDE_EFFECT_CLASS[tool.sideEffect],
                )}
              >
                {tool.sideEffect}
              </span>
            </span>
            <span className="mt-2 block text-muted-foreground">
              {tool.description}
            </span>
            <span className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>{tool.owner}</span>
              <span>{tool.usage7d.toLocaleString()} calls / 7d</span>
              <span>{tool.evalCoveragePercent}% eval</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function SchemaTable({ fields }: { fields: ToolsRoomTool["schema"] }) {
  if (fields.length === 0) {
    return (
      <p className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
        No schema captured yet.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-left text-sm">
        <thead className="text-xs text-muted-foreground">
          <tr className="border-b">
            <th className="py-2 pr-3 font-medium">Argument</th>
            <th className="py-2 pr-3 font-medium">Type</th>
            <th className="py-2 pr-3 font-medium">Required</th>
            <th className="py-2 pr-3 font-medium">Sensitive</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <tr key={field.name} className="border-b last:border-0">
              <td className="py-2 pr-3 font-medium">{field.name}</td>
              <td className="py-2 pr-3 text-muted-foreground">{field.type}</td>
              <td className="py-2 pr-3">{field.required ? "Yes" : "No"}</td>
              <td className="py-2 pr-3">
                {field.sensitive ? "Vault only" : "No"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailPanel({ tool }: { tool: ToolsRoomTool | null }) {
  if (!tool) {
    return (
      <StatePanel state="empty" title="No tool selected">
        <p>Select a catalog row to inspect schema, auth, safety, and grants.</p>
      </StatePanel>
    );
  }
  const stateTreatment = OBJECT_STATE_TREATMENTS[tool.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[tool.trust];
  const grantBlocked = tool.productionGrant !== "approved";

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby="tool-detail-heading"
      data-testid="tools-room-detail"
    >
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Tool detail
          </p>
          <h3 className="mt-1 text-lg font-semibold" id="tool-detail-heading">
            {tool.name}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">{tool.source}</p>
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
              SIDE_EFFECT_CLASS[tool.sideEffect],
            )}
          >
            {tool.sideEffect}
          </span>
        </div>

        <section className="rounded-md border bg-background p-3">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Braces className="h-4 w-4" aria-hidden />
            Input schema
          </p>
          <SchemaTable fields={tool.schema} />
        </section>

        <section className="rounded-md border bg-background p-3">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Braces className="h-4 w-4" aria-hidden />
            Output schema
          </p>
          <SchemaTable fields={tool.outputSchema} />
        </section>

        <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,10rem),1fr))]">
          <Metric
            label="Usage"
            value={tool.usage7d.toLocaleString()}
            detail="Calls over 7 days"
          />
          <Metric
            label="Failure"
            value={`${tool.failureRate}%`}
            detail={tool.safety.failureMode}
          />
          <Metric
            label="Cost"
            value={formatUsd(tool.costPer1kUsd)}
            detail="Per 1,000 calls"
          />
          <Metric
            label="Success"
            value={`${tool.successRatePercent}%`}
            detail="Successful calls over 7 days"
          />
          <Metric
            label="P95 latency"
            value={`${tool.p95LatencyMs} ms`}
            detail="Production or staging p95"
          />
          <Metric
            label="Retry rate"
            value={`${tool.retryRatePercent}%`}
            detail={`${tool.failedCalls7d} failed calls / 7d`}
          />
          <Metric
            label="PII sent"
            value={tool.piiSent7d.toLocaleString()}
            detail="Arguments classified as personal data"
          />
          <Metric
            label="Schema change"
            value={formatTimestamp(tool.lastSchemaChangeAt)}
            detail="Last contract-shape update"
          />
        </section>

        <ConfidenceMeter
          value={tool.evalCoveragePercent}
          level={tool.evalConfidence}
          label="Eval coverage"
          evidence={`Evidence: ${tool.evidence.join(", ")}`}
        />

        <section
          className="rounded-md border bg-background p-3"
          data-testid="tools-room-auth"
        >
          <p className="flex items-center gap-2 text-sm font-semibold">
            <KeyRound className="h-4 w-4" aria-hidden />
            Auth and secret boundary
          </p>
          <dl className="mt-2 grid gap-2 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
            <div>
              <dt className="text-muted-foreground">Auth</dt>
              <dd>{tool.authMode}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Secret reference</dt>
              <dd className="break-words">{tool.secretRef}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">KMS key</dt>
              <dd className="break-words">{tool.kmsKeyRef}</dd>
            </div>
          </dl>
        </section>

        <section
          className="rounded-md border bg-background p-3"
          data-testid="tools-room-contract-fields"
        >
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ClipboardList className="h-4 w-4" aria-hidden />
            Implementation contract
          </p>
          <dl className="mt-2 grid gap-2 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))]">
            <div>
              <dt className="text-muted-foreground">Environment</dt>
              <dd>{tool.environment}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Timeout</dt>
              <dd>{tool.timeoutMs} ms</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Rate limit</dt>
              <dd>{tool.rateLimit}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Retry policy</dt>
              <dd>{tool.retryPolicy}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Idempotency</dt>
              <dd>{tool.idempotency}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Data classification</dt>
              <dd>{tool.dataClassification}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Allowed agents</dt>
              <dd>{tool.safety.agentsAllowed.join(", ")}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Allowed channels</dt>
              <dd>{tool.allowedChannels.join(", ") || "Review required"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Approval requirements</dt>
              <dd>{tool.approvalRequirements}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Audit requirements</dt>
              <dd>{tool.auditRequirements}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">
                Compensation / rollback
              </dt>
              <dd>{tool.compensationBehavior}</dd>
            </div>
          </dl>
        </section>

        <RiskHalo
          level={grantBlocked ? "blocked" : "low"}
          label={tool.productionBoundary}
        >
          <div
            className="rounded-md bg-background p-3"
            data-testid="tools-room-production-boundary"
          >
            <p className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4" aria-hidden />
              Production grant boundary
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {tool.productionBoundary}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Next: {tool.productionNextStep}
            </p>
            <button
              type="button"
              disabled={grantBlocked}
              title={grantBlocked ? tool.productionNextStep : undefined}
              className="mt-3 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
              data-testid="tools-room-grant-production"
            >
              Grant production
            </button>
          </div>
        </RiskHalo>
      </div>
    </section>
  );
}

function SafetyContract({ tool }: { tool: ToolsRoomTool | null }) {
  if (!tool) return null;
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="tools-room-safety"
    >
      <p className="flex items-center gap-2 text-sm font-semibold">
        <ClipboardList className="h-4 w-4" aria-hidden />
        Safety contract
      </p>
      <dl className="mt-3 grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
        <div>
          <dt className="text-muted-foreground">Mutates data</dt>
          <dd>{tool.safety.mutatesData ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Can spend money</dt>
          <dd>{tool.safety.spendsMoney ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Personal data exposure</dt>
          <dd>{tool.safety.exposesPersonalData ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Audit event</dt>
          <dd>{tool.safety.auditEvent}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">
        Evidence: {tool.safety.evidence}
      </p>
    </section>
  );
}

function formatRecord(record: Record<string, unknown>): string {
  const entries = Object.entries(record);
  if (entries.length === 0) return "Not set";
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(", ");
}

function ToolContractQuestionnaire({
  agentId,
  tool,
  contract,
  onPromoted,
}: {
  agentId: string;
  tool: ToolsRoomTool | null;
  contract: ToolContract | null;
  onPromoted: (contract: ToolContract) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!tool) return null;
  if (!contract) {
    return (
      <section
        className="min-w-0 rounded-md border bg-card p-4"
        data-testid="tool-contract-panel"
      >
        <p className="text-sm font-semibold">Tool contract</p>
        <p className="mt-2 text-sm text-muted-foreground">
          No durable contract exists yet. Save the safety questionnaire before
          this tool can leave sandbox.
        </p>
      </section>
    );
  }
  const activeContract = contract;

  async function promoteContract() {
    setBusy(true);
    setError(null);
    try {
      const promoted = await promoteToolContract(
        agentId,
        activeContract.tool_id,
      );
      onPromoted(promoted);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Promotion failed.");
    } finally {
      setBusy(false);
    }
  }

  const canPromote =
    contract.live_status !== "approved" &&
    contract.live_status !== "blocked" &&
    !contract.approval_invalidated_at;

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="tool-contract-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ClipboardList className="h-4 w-4" aria-hidden />
            Tool contract
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Durable permission contract for sandbox, live promotion, money caps,
            owner, and approval invalidation.
          </p>
        </div>
        <LiveBadge
          tone={
            contract.live_status === "approved"
              ? "live"
              : contract.live_status === "blocked"
                ? "paused"
                : "draft"
          }
        >
          {contract.live_status.replace(/_/g, " ")}
        </LiveBadge>
      </div>

      <dl className="mt-3 grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
        <div>
          <dt className="text-muted-foreground">Sandbox</dt>
          <dd>{contract.sandbox_status}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Side effect</dt>
          <dd>{contract.side_effect_level.replace(/_/g, " ")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Owner</dt>
          <dd>{contract.owner_user_id || "Unassigned"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Money caps</dt>
          <dd>{formatRecord(contract.budget_limits)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Rate limits</dt>
          <dd>{formatRecord(contract.rate_limits)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Approval policy</dt>
          <dd>{contract.approval_policy_id || "Not set"}</dd>
        </div>
      </dl>

      {contract.approval_invalidated_at ? (
        <p className="mt-3 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-muted-foreground">
          Approval invalidated at {contract.approval_invalidated_at}. Re-review
          this contract before live use.
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!canPromote || busy}
          onClick={() => void promoteContract()}
          data-testid="tool-contract-promote"
        >
          {busy
            ? "Promoting"
            : contract.live_status === "approved"
              ? "Live approved"
              : "Promote contract live"}
        </button>
        <span className="text-xs text-muted-foreground">
          Hash {contract.content_hash.slice(0, 10)}
        </span>
      </div>
      {error ? (
        <p className="mt-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

function MockLivePanel({ tool }: { tool: ToolsRoomTool | null }) {
  if (!tool) return null;
  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="tools-room-mock-live"
    >
      <p className="text-sm font-semibold">Mock and live status</p>
      <div className="mt-3 grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Mock
          </p>
          <p className="mt-1 text-sm">{tool.mockStatus}</p>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Live
          </p>
          <p className="mt-1 text-sm">{tool.liveStatus}</p>
        </div>
      </div>
      <pre className="mt-3 overflow-auto rounded-md bg-muted p-3 text-xs leading-5">
        <code>{tool.mockResponse}</code>
      </pre>
    </section>
  );
}

export function ToolsRoom({ data }: ToolsRoomProps) {
  const [selectedToolId, setSelectedToolId] = useState<string | null>(
    data.tools[0]?.id ?? null,
  );
  const [contracts, setContracts] = useState<ToolContract[]>(
    data.toolContracts,
  );
  const selectedTool = useMemo(
    () =>
      data.tools.find((tool) => tool.id === selectedToolId) ??
      data.tools[0] ??
      null,
    [data.tools, selectedToolId],
  );
  const selectedContract =
    contracts.find((contract) => contract.tool_id === selectedTool?.id) ?? null;
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];
  const totalUsage = data.tools.reduce((sum, tool) => sum + tool.usage7d, 0);
  const blockedCount = data.tools.filter(
    (tool) => tool.productionGrant === "blocked",
  ).length;

  return (
    <div className="flex flex-col gap-6" data-testid="tools-room">
      <section className="rounded-md border bg-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Tools Room
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
        <p className="mt-3 text-sm text-muted-foreground">
          Catalog, schema, auth, side effects, mocks, live grants, usage, cost,
          failure, eval coverage, and production boundaries for every tool this
          agent can call.
        </p>
      </section>

      {data.degradedReason ? (
        <StatePanel state="degraded" title="Tool catalog is empty">
          <p>{data.degradedReason}</p>
        </StatePanel>
      ) : null}

      <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr))]">
        <Metric
          label="Bound tools"
          value={`${data.tools.length}`}
          detail={data.catalogEvidence}
        />
        <Metric
          label="Usage"
          value={totalUsage.toLocaleString()}
          detail="Calls over 7 days"
        />
        <Metric
          label="Blocked grants"
          value={`${blockedCount}`}
          detail="Production boundaries active"
        />
      </section>

      <section className="grid min-w-0 gap-4">
        <Catalog
          tools={data.tools}
          selectedId={selectedTool?.id ?? null}
          onSelect={setSelectedToolId}
        />
        <DetailPanel tool={selectedTool} />
        <SafetyContract tool={selectedTool} />
        <ToolContractQuestionnaire
          agentId={data.agentId}
          tool={selectedTool}
          contract={selectedContract}
          onPromoted={(contract) =>
            setContracts((current) => {
              const exists = current.some((item) => item.id === contract.id);
              if (exists) {
                return current.map((item) =>
                  item.id === contract.id ? contract : item,
                );
              }
              return [contract, ...current];
            })
          }
        />
        <MockLivePanel tool={selectedTool} />
        <InstantToolImport agentId={data.agentId} />
        <EvidenceCallout
          title="Secret values stay out of Studio"
          source="SECURITY.md §3; CLOUD_PORTABILITY.md §4.3; ENV_REFERENCE.md §9"
          confidence={100}
          confidenceLevel="high"
          tone="success"
          className="min-w-0"
        >
          <p>
            Tool credentials are represented as Vault references and KMS key
            refs. Imported requests redact auth values before drafts are shown.
          </p>
        </EvidenceCallout>
      </section>
    </div>
  );
}
