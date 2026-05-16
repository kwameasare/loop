import Link from "next/link";
import type { ReactNode } from "react";

import { SectionDegraded, SectionEmpty } from "@/components/section-states";
import type { AuditEventRow } from "@/components/workspaces/audit-log-page";
import {
  fetchCurrentCommitment,
  type CommitmentDocument,
} from "@/lib/agent-commitment";
import {
  listAgentSecrets,
  type AgentSecret,
} from "@/lib/agent-secrets";
import { listAuditEvents } from "@/lib/audit-events";
import { PreApprovedClassesPanel } from "@/components/governance/pre-approved-classes-panel";
import {
  listPreApprovedClasses,
  type PreApprovedClass,
} from "@/lib/pre-approved-classes";
import { getAgentDetailData } from "../agent-detail-data";

interface PageProps {
  params: { agent_id: string };
  searchParams?:
    | {
        view?: string | string[] | undefined;
      }
    | undefined;
}

interface GovernanceEvidence {
  commitment?: CommitmentDocument | undefined;
  secrets: AgentSecret[];
  preApprovedClasses: PreApprovedClass[];
  auditEvents: AuditEventRow[];
  auditLoaded: boolean;
  degradedReasons: string[];
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "Not recorded";
}

function compactHash(hash: string): string {
  if (!hash || hash === "unconfigured") return hash || "Not recorded";
  return hash.length > 16 ? `${hash.slice(0, 10)}...${hash.slice(-6)}` : hash;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Date(timestamp).toISOString().replace(".000Z", "Z");
}

function isAgentAuditEvent(event: AuditEventRow, agentId: string): boolean {
  const resource = `${event.resourceType} ${event.resourceId ?? ""}`;
  return (
    event.resourceId === agentId ||
    event.resourceId?.includes(agentId) === true ||
    resource.includes(agentId)
  );
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

async function loadGovernanceEvidence(
  agentId: string,
  workspaceId: string,
): Promise<GovernanceEvidence> {
  const degradedReasons: string[] = [];

  const commitment = await fetchCurrentCommitment(agentId).catch((error) => {
    degradedReasons.push(
      messageFromError(error, "Could not load the current commitment document."),
    );
    return undefined;
  });

  const secrets = await listAgentSecrets(agentId)
    .then((result) => {
      if (result.degraded_reason) degradedReasons.push(result.degraded_reason);
      return result.items;
    })
    .catch((error: unknown) => {
      degradedReasons.push(
        messageFromError(error, "Could not load agent secret references."),
      );
      return [];
    });

  const preApprovedClasses = await listPreApprovedClasses(agentId)
    .then((result) => result.items)
    .catch((error: unknown) => {
      degradedReasons.push(
        messageFromError(error, "Could not load pre-approved classes."),
      );
      return [];
    });

  let auditEvents: AuditEventRow[] = [];
  let auditLoaded = false;
  if (!workspaceId || workspaceId === "unavailable") {
    degradedReasons.push(
      "Workspace context is unavailable, so Studio cannot request agent-scoped audit evidence.",
    );
  } else {
    try {
      const result = await listAuditEvents(workspaceId, { limit: 100 });
      auditEvents = result.events.filter((event) =>
        isAgentAuditEvent(event, agentId),
      );
      auditLoaded = true;
    } catch (error) {
      degradedReasons.push(
        messageFromError(error, "Could not load agent audit events."),
      );
    }
  }

  return {
    commitment,
    secrets,
    preApprovedClasses,
    auditEvents,
    auditLoaded,
    degradedReasons,
  };
}

function EvidenceCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="instrument-panel rounded-2xl p-4">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function FieldList({
  fields,
}: {
  fields: Array<{ label: string; value: string }>;
}) {
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      {fields.map((field) => (
        <div
          key={field.label}
          className="rounded-md border bg-background/60 p-3"
        >
          <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            {field.label}
          </dt>
          <dd className="mt-1 break-words font-medium">{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default async function AgentGovernancePage({
  params,
  searchParams,
}: PageProps) {
  const { agent, degradedReason: agentDegradedReason } =
    await getAgentDetailData(params.agent_id);
  const evidence = await loadGovernanceEvidence(
    params.agent_id,
    agent.workspace_id,
  );
  const degradedEvidence = [
    agentDegradedReason,
    ...evidence.degradedReasons,
  ]
    .filter(Boolean)
    .join(" ");
  const missingCommitmentFields =
    evidence.commitment?.structured_summary.missing_required_fields ?? [];
  const commitmentChannels =
    evidence.commitment?.structured_summary.channels ?? [];

  const commitmentFields = [
    {
      label: "Status",
      value: evidence.commitment?.status ?? "Unavailable",
    },
    {
      label: "Content hash",
      value: evidence.commitment
        ? compactHash(evidence.commitment.content_hash)
        : "Not loaded",
    },
    {
      label: "Version",
      value: evidence.commitment
        ? String(evidence.commitment.version)
        : "Not loaded",
    },
    {
      label: "Owner",
      value: formatValue(
        evidence.commitment?.structured_summary.owner ||
          evidence.commitment?.owner_user_id,
      ),
    },
    {
      label: "Readiness",
      value: evidence.commitment?.structured_summary.readiness ?? "Unverified",
    },
    {
      label: "Updated",
      value: formatTimestamp(evidence.commitment?.updated_at),
    },
  ];

  const postureFields = [
    {
      label: "Workspace",
      value: formatValue(agent.workspace_id),
    },
    {
      label: "Agent state",
      value: agent.object_state.replace(/_/g, " "),
    },
    {
      label: "Secret references",
      value:
        evidence.secrets.length > 0
          ? `${evidence.secrets.length} reference${
              evidence.secrets.length === 1 ? "" : "s"
            } loaded`
          : evidence.degradedReasons.some((reason) =>
                reason.toLowerCase().includes("secret"),
              )
            ? "Unverified"
            : "None returned",
    },
    {
      label: "Audit trail",
      value: evidence.auditLoaded
        ? `${evidence.auditEvents.length} agent event${
            evidence.auditEvents.length === 1 ? "" : "s"
          }`
        : "Unverified",
    },
    {
      label: "Pre-approved classes",
      value: `${evidence.preApprovedClasses.filter(
        (item) => item.status === "active",
      ).length} active`,
    },
  ];
  const evidenceLinks = [
    { label: "Trace evidence", href: `/agents/${params.agent_id}/traces` },
    { label: "Eval evidence", href: `/agents/${params.agent_id}/evals` },
    { label: "Deploy evidence", href: `/agents/${params.agent_id}/deploys` },
    { label: "Incident evidence", href: `/agents/${params.agent_id}/observe` },
    {
      label: "Workspace audit",
      href: `/enterprise/audit?agent_id=${encodeURIComponent(params.agent_id)}`,
    },
  ];
  const focusedView = firstParam(searchParams?.view);
  const auditFocused = focusedView === "audit";
  const channelsFocused = focusedView === "channels";

  return (
    <section className="space-y-5" data-testid="agent-governance-page">
      <header className="instrument-panel rounded-2xl p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Agent Workbench / Governance
        </p>
        <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-normal">
              Governance evidence for {agent.name || params.agent_id}
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Verify the commitment hash, secret boundary, audit trail, and
              evidence path before production-impacting changes. Unavailable
              governance systems are shown as degraded, not as passing.
            </p>
          </div>
          <Link
            href={`/enterprise/govern?agent_id=${encodeURIComponent(
              params.agent_id,
            )}`}
            className="inline-flex w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            Open governance center
          </Link>
        </div>
      </header>

      {focusedView ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-4 text-sm text-info"
          data-testid="governance-focused-view"
        >
          <p className="font-medium">Opened from an evidence link.</p>
          <p className="mt-1 text-xs">
            {auditFocused
              ? "Agent-scoped audit events are highlighted below."
              : channelsFocused
                ? "Channel compliance readiness is highlighted below."
                : `Requested governance view: ${focusedView}.`}
          </p>
        </section>
      ) : null}

      {degradedEvidence ? (
        <SectionDegraded
          title="Agent governance"
          description="Agent-scoped governance evidence could not fully load from the control plane. Studio will not claim approvals, secrets, auditability, or residency posture without source evidence."
          evidence={degradedEvidence}
        />
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <EvidenceCard
          title="Commitment and content hash"
          description="The accepted commitment is the object approvals bind to. Editing after approval must create a different hash and require renewed approval."
        >
          <FieldList fields={commitmentFields} />
          {missingCommitmentFields.length > 0 ? (
            <p className="mt-3 rounded-md border border-dashed p-3 text-sm text-muted-foreground">
              Missing required fields: {missingCommitmentFields.join(", ")}
            </p>
          ) : null}
        </EvidenceCard>

        <EvidenceCard
          title="Secret boundary"
          description="Studio may show secret references and rotation evidence. It must never display secret values in the builder UI."
        >
          {evidence.secrets.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {evidence.secrets.map((secret) => (
                <li
                  key={secret.id}
                  className="rounded-md border bg-background/60 p-3"
                >
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <span className="font-medium">{secret.name}</span>
                    <span className="text-xs text-muted-foreground">
                      rotated {formatTimestamp(secret.rotated_at)}
                    </span>
                  </div>
                  <p className="mt-1 break-words text-xs text-muted-foreground">
                    ref: {secret.ref}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
              No secret references were returned for this agent. This is only a
              clean state when the vault endpoint loaded successfully.
            </p>
          )}
        </EvidenceCard>

        <EvidenceCard
          title="Governance posture"
          description="These checks summarize what Studio can prove from the loaded agent evidence. Unverified checks remain explicit."
        >
          <FieldList fields={postureFields} />
        </EvidenceCard>

        <EvidenceCard
          title="Pre-approved classes"
          description="Narrow, explicit, time-boxed approval corridors for low-risk changes. They must stay inspectable and revocable."
        >
          <PreApprovedClassesPanel
            agentId={params.agent_id}
            initialItems={evidence.preApprovedClasses}
          />
        </EvidenceCard>

        {channelsFocused ? (
          <section
            className="instrument-panel rounded-2xl p-4 ring-2 ring-focus ring-offset-2 ring-offset-background"
            data-testid="governance-channel-readiness"
            data-focused="true"
          >
            <h3 className="text-base font-semibold">
              Channel compliance readiness
            </h3>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Channel changes must prove transcript capture, regional routing,
              consent posture, and rollback evidence before production rollout.
            </p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div className="rounded-md border bg-background/60 p-3">
                <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
                  Declared channels
                </dt>
                <dd className="mt-1 break-words font-medium">
                  {commitmentChannels.length > 0
                    ? commitmentChannels.join(", ")
                    : "Not recorded"}
                </dd>
              </div>
              <div className="rounded-md border bg-background/60 p-3">
                <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
                  Evidence route
                </dt>
                <dd className="mt-1 break-words font-medium">
                  /agents/{params.agent_id}/channels
                </dd>
              </div>
            </dl>
            <Link
              href={`/agents/${params.agent_id}/channels?view=readiness`}
              className="mt-4 inline-flex w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              Open channel readiness
            </Link>
          </section>
        ) : null}

        <EvidenceCard
          title="Evidence export path"
          description="Auditors need links from this agent to traces, evals, deploys, approvals, incidents, and handoffs."
        >
          <div className="flex flex-wrap gap-2">
            {evidenceLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </EvidenceCard>
      </div>

      <section
        className={`instrument-panel rounded-2xl p-4 ${
          auditFocused ? "ring-2 ring-focus ring-offset-2 ring-offset-background" : ""
        }`}
        data-focused={auditFocused ? "true" : "false"}
        data-testid="agent-governance-audit-section"
      >
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-base font-semibold">Recent audit events</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Agent-related workspace writes, denies, and errors. Empty means
              the audit endpoint responded and no matching agent events were
              returned.
            </p>
          </div>
          <Link
            href={`/enterprise/audit?agent_id=${encodeURIComponent(
              params.agent_id,
            )}`}
            className="inline-flex w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            Open audit log
          </Link>
        </div>

        {evidence.auditEvents.length > 0 ? (
          <ul className="mt-4 divide-y rounded-md border">
            {evidence.auditEvents.slice(0, 6).map((event) => (
              <li key={event.id} className="grid gap-2 p-3 text-sm md:grid-cols-4">
                <span className="font-medium">{event.action}</span>
                <span className="text-muted-foreground">{event.actorSub}</span>
                <span className="text-muted-foreground">
                  {event.resourceType}:{formatValue(event.resourceId)}
                </span>
                <span className="text-muted-foreground">
                  {formatTimestamp(event.occurredAt)} / {event.outcome}
                </span>
              </li>
            ))}
          </ul>
        ) : evidence.auditLoaded ? (
          <div className="mt-4">
            <SectionEmpty
              title="Agent audit events"
              description="The audit endpoint loaded, but no events were tied to this agent in the returned window."
              evidence={`workspace=${agent.workspace_id}; agent=${params.agent_id}`}
            />
          </div>
        ) : null}
      </section>
    </section>
  );
}
