"use client";

import { useMemo, useState, type FormEvent } from "react";
import { CheckCircle2, FileText, History, ShieldAlert } from "lucide-react";

import { SectionDegraded } from "@/components/section-states";
import {
  type CommitmentBody,
  type CommitmentDocument,
  type CommitmentDraftInput,
  EMPTY_COMMITMENT_BODY,
  buildLocalCommitmentDocument,
  commitmentFieldLabel,
  missingCommitmentFields,
  parseList,
  saveCommitmentDraft as defaultSaveCommitmentDraft,
  acceptCommitment as defaultAcceptCommitment,
} from "@/lib/agent-commitment";
import { cn } from "@/lib/utils";

interface AgentContractPanelProps {
  agentId: string;
  initialDocument?: CommitmentDocument | null | undefined;
  initialHistory?: CommitmentDocument[] | undefined;
  focusedCommitmentId?: string | undefined;
  degradedReason?: string | undefined;
  historyDegradedReason?: string | undefined;
  saveDraft?: (
    agentId: string,
    input: CommitmentDraftInput,
  ) => Promise<CommitmentDocument>;
  acceptCommitment?: (agentId: string) => Promise<CommitmentDocument>;
}

type FormState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "accepting" }
  | { kind: "saved"; message: string }
  | { kind: "error"; message: string };

const TEXTAREA_CLASS =
  "min-h-20 rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";
const INPUT_CLASS =
  "rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function listText(items: string[]): string {
  return items.join(", ");
}

function setTextField<K extends keyof CommitmentBody>(
  body: CommitmentBody,
  field: K,
  value: CommitmentBody[K],
): CommitmentBody {
  return { ...body, [field]: value };
}

function summaryLine(
  document: CommitmentDocument,
  missingCount: number,
): string {
  if (document.status === "accepted") {
    return `Accepted v${document.version}. Deploys can reference this contract hash.`;
  }
  if (missingCount === 0) {
    return `Draft v${document.version || 1} is complete and ready for acceptance.`;
  }
  return `Draft v${document.version || 1} still needs ${missingCount} required field${
    missingCount === 1 ? "" : "s"
  }.`;
}

function sortHistory(
  history: readonly CommitmentDocument[],
): CommitmentDocument[] {
  return [...history].sort((left, right) => right.version - left.version);
}

function upsertHistory(
  history: readonly CommitmentDocument[],
  next: CommitmentDocument,
): CommitmentDocument[] {
  const withoutCurrent = history.filter((item) => item.id !== next.id);
  return sortHistory([...withoutCurrent, next]);
}

function isLoadedCommitment(document: CommitmentDocument): boolean {
  return (
    document.id !== "commitment_unconfigured" &&
    document.content_hash !== "unconfigured" &&
    document.created_from !== "studio:local_unconfigured"
  );
}

export function AgentContractPanel({
  agentId,
  initialDocument,
  initialHistory,
  focusedCommitmentId,
  degradedReason,
  historyDegradedReason,
  saveDraft = defaultSaveCommitmentDraft,
  acceptCommitment = defaultAcceptCommitment,
}: AgentContractPanelProps) {
  const fallbackDocument = useMemo(
    () => buildLocalCommitmentDocument(agentId),
    [agentId],
  );
  const [document, setDocument] = useState(initialDocument ?? fallbackDocument);
  const [history, setHistory] = useState<CommitmentDocument[]>(
    sortHistory(
      initialHistory && initialHistory.length > 0
        ? initialHistory
        : initialDocument
          ? [initialDocument]
          : [],
    ),
  );
  const [body, setBody] = useState<CommitmentBody>(
    initialDocument?.body ?? EMPTY_COMMITMENT_BODY,
  );
  const [state, setState] = useState<FormState>({ kind: "idle" });
  const missing = useMemo(() => missingCommitmentFields(body), [body]);
  const completeness = Math.round(((8 - missing.length) / 8) * 100);
  const busy = state.kind === "saving" || state.kind === "accepting";
  const loadedCommitment = isLoadedCommitment(document);
  const backendUnavailable = Boolean(degradedReason) || !loadedCommitment;
  const focusedHistoryItem = history.find(
    (item) => focusedCommitmentId && item.id === focusedCommitmentId,
  );
  const isFocused = Boolean(focusedHistoryItem);

  async function handleSave(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setState({ kind: "saving" });
    try {
      const updated = await saveDraft(agentId, {
        body,
        created_from: "studio:agent_contract",
      });
      setDocument(updated);
      setState({
        kind: "saved",
        message: `Draft v${updated.version || 1} saved.`,
      });
      setHistory((current) => upsertHistory(current, updated));
      return updated;
    } catch (error) {
      setState({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to save the Agent Contract.",
      });
      return null;
    }
  }

  async function handleAccept() {
    if (missing.length > 0 || busy) return;
    setState({ kind: "accepting" });
    try {
      const draft = await saveDraft(agentId, {
        body,
        created_from: "studio:agent_contract_accept",
      });
      const accepted = await acceptCommitment(agentId);
      const acceptedDocument =
        accepted.version === 0
          ? {
              ...draft,
              status: "accepted" as const,
              accepted_at: new Date().toISOString(),
            }
          : accepted;
      setDocument(acceptedDocument);
      setBody(acceptedDocument.body);
      setHistory((current) => upsertHistory(current, acceptedDocument));
      setState({
        kind: "saved",
        message: `Contract v${acceptedDocument.version || 1} accepted.`,
      });
    } catch (error) {
      setState({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to accept the Agent Contract.",
      });
    }
  }

  function updateText<K extends keyof CommitmentBody>(
    field: K,
    value: CommitmentBody[K],
  ) {
    setBody((current) => setTextField(current, field, value));
  }

  return (
    <section
      className={cn(
        "space-y-5",
        isFocused
          ? "rounded-md ring-2 ring-focus ring-offset-2 ring-offset-background"
          : "",
      )}
      data-testid="agent-contract-panel"
      data-focused={isFocused ? "true" : "false"}
    >
      {degradedReason ? (
        <div data-testid="contract-degraded">
          <SectionDegraded
            title="Agent Contract"
            description="The current Commitment Document could not load from the control plane. The local form is visible for review, but save and accept are disabled until backend evidence is available."
            evidence={degradedReason}
          />
        </div>
      ) : null}
      {isFocused ? (
        <p
          className="rounded-md border border-info/40 bg-info/5 px-3 py-2 text-sm text-info"
          data-testid="contract-focused"
        >
          Opened from evidence link: Commitment Document{" "}
          {focusedHistoryItem?.id} is focused.
        </p>
      ) : null}
      <div className="rounded-md border bg-card p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <FileText className="h-4 w-4" aria-hidden />
              Agent Contract
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-normal">
              Commitment Document
            </h2>
            <p
              className="mt-2 max-w-3xl text-sm text-muted-foreground"
              data-testid="contract-summary-line"
            >
              {loadedCommitment
                ? summaryLine(document, missing.length)
                : "Commitment Document is unavailable. Studio can show the contract fields, but it will not call this a saved draft until the control plane returns a durable document."}
            </p>
          </div>
          <div className="grid min-w-48 gap-2 rounded-md border bg-background p-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Status</span>
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-xs font-medium",
                  document.status === "accepted"
                    ? "border-success/40 bg-success/10 text-success"
                    : "border-warning/50 bg-warning/10 text-warning",
                )}
                data-testid="contract-status"
              >
                {loadedCommitment ? document.status : "unavailable"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Version</span>
              <span data-testid="contract-version">
                {loadedCommitment ? `v${document.version || 1}` : "Not loaded"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Complete</span>
              <span data-testid="contract-completeness">{completeness}%</span>
            </div>
          </div>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-300"
            style={{ width: `${completeness}%` }}
            aria-hidden
          />
        </div>
      </div>

      {missing.length > 0 ? (
        <div
          className="rounded-md border border-warning/50 bg-warning/10 p-4"
          data-testid="contract-missing-fields"
        >
          <div className="flex items-start gap-2">
            <ShieldAlert className="mt-0.5 h-4 w-4 text-warning" aria-hidden />
            <div>
              <p className="text-sm font-medium">Required before acceptance</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {missing.map(commitmentFieldLabel).join(", ")}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="rounded-md border border-success/40 bg-success/10 p-4"
          data-testid="contract-ready"
        >
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 text-success" aria-hidden />
            <div>
              <p className="text-sm font-medium">Ready to accept</p>
              <p className="mt-1 text-sm text-muted-foreground">
                This contract has the required owner, scope, failure mode,
                channel, system, region, and language commitments.
              </p>
            </div>
          </div>
        </div>
      )}

      <section
        className="rounded-md border bg-card"
        data-testid="contract-version-history"
      >
        <div className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <History className="h-4 w-4" aria-hidden />
              Version history
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Every saved or accepted Commitment Document version remains
              inspectable because preflight and production deploys cite the
              exact version they reviewed.
            </p>
          </div>
          <span className="rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground">
            {history.length} version{history.length === 1 ? "" : "s"}
          </span>
        </div>
        {historyDegradedReason ? (
          <p
            className="m-4 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning"
            data-testid="contract-history-degraded"
          >
            {historyDegradedReason}
          </p>
        ) : null}
        {history.length > 0 ? (
          <ol className="divide-y">
            {history.map((item) => (
              <li
                key={item.id}
                className={cn(
                  "grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto]",
                  focusedCommitmentId === item.id
                    ? "bg-info/5 ring-1 ring-inset ring-info/30"
                    : "",
                )}
                data-testid={`contract-history-${item.id}`}
                data-focused={
                  focusedCommitmentId === item.id ? "true" : "false"
                }
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">
                      Commitment v{item.version || 1}
                    </span>
                    <span
                      className={cn(
                        "rounded-full border px-2 py-0.5 text-xs font-medium",
                        item.status === "accepted"
                          ? "border-success/40 bg-success/10 text-success"
                          : item.status === "draft"
                            ? "border-warning/50 bg-warning/10 text-warning"
                            : "bg-muted text-muted-foreground",
                      )}
                    >
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {item.structured_summary.responsibility ||
                      item.body.business_responsibility ||
                      "Responsibility not described"}
                  </p>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">
                    {item.id} · hash {item.content_hash.slice(0, 12)} ·{" "}
                    {item.created_from}
                  </p>
                </div>
                <div className="text-left text-xs text-muted-foreground md:text-right">
                  <p>Updated {item.updated_at || "unknown"}</p>
                  <p>
                    {item.accepted_at
                      ? `Accepted ${item.accepted_at}`
                      : "Not accepted"}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="p-4 text-sm text-muted-foreground">
            No Commitment Document version history loaded.
          </p>
        )}
      </section>

      <form onSubmit={handleSave} className="grid gap-5" noValidate>
        <div className="grid gap-4 rounded-md border bg-card p-5">
          <div>
            <h3 className="text-base font-semibold">Mission and risk</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              The contract must make the agent&apos;s job, user set, and failure
              boundary readable without opening behavior config.
            </p>
          </div>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Business responsibility</span>
            <textarea
              value={body.business_responsibility}
              onChange={(event) =>
                updateText("business_responsibility", event.target.value)
              }
              className={TEXTAREA_CLASS}
              data-testid="contract-business-responsibility"
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Target users</span>
              <textarea
                value={body.target_users}
                onChange={(event) =>
                  updateText("target_users", event.target.value)
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-target-users"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Worst-case failure</span>
              <textarea
                value={body.worst_case_failure}
                onChange={(event) =>
                  updateText("worst_case_failure", event.target.value)
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-worst-case-failure"
              />
            </label>
          </div>
        </div>

        <div className="grid gap-4 rounded-md border bg-card p-5">
          <div>
            <h3 className="text-base font-semibold">Ownership and rollout</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Enterprise agents need clear humans, regions, language coverage,
              launch intent, and operating budget.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Owner</span>
              <input
                value={body.owner_user_id}
                onChange={(event) =>
                  updateText("owner_user_id", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-owner"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Backup owner</span>
              <input
                value={body.backup_owner_user_id}
                onChange={(event) =>
                  updateText("backup_owner_user_id", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-backup-owner"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Success metric</span>
              <input
                value={body.success_metric}
                onChange={(event) =>
                  updateText("success_metric", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-success-metric"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Budget target</span>
              <input
                value={body.budget_target}
                onChange={(event) =>
                  updateText("budget_target", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-budget-target"
              />
            </label>
          </div>
        </div>

        <div className="grid gap-4 rounded-md border bg-card p-5">
          <div>
            <h3 className="text-base font-semibold">Channels and systems</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Voice is one channel. Web chat, WhatsApp, Telegram, Slack, Teams,
              SMS, email, and webhooks are equally valid bindings.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Channels</span>
              <textarea
                value={listText(body.channels)}
                onChange={(event) =>
                  updateText("channels", parseList(event.target.value))
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-channels"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Systems touched</span>
              <textarea
                value={listText(body.systems_touched)}
                onChange={(event) =>
                  updateText("systems_touched", parseList(event.target.value))
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-systems"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Regions</span>
              <textarea
                value={listText(body.regions)}
                onChange={(event) =>
                  updateText("regions", parseList(event.target.value))
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-regions"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Languages</span>
              <textarea
                value={listText(body.languages)}
                onChange={(event) =>
                  updateText("languages", parseList(event.target.value))
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-languages"
              />
            </label>
          </div>
        </div>

        <div className="grid gap-4 rounded-md border bg-card p-5">
          <div>
            <h3 className="text-base font-semibold">Boundaries</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              These fields help reviewers understand where the agent must stop,
              escalate, and produce evidence.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Compliance domain</span>
              <input
                value={body.compliance_domain}
                onChange={(event) =>
                  updateText("compliance_domain", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-compliance-domain"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Expected volume</span>
              <input
                value={body.expected_volume}
                onChange={(event) =>
                  updateText("expected_volume", event.target.value)
                }
                className={INPUT_CLASS}
                data-testid="contract-expected-volume"
              />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Out of scope</span>
              <textarea
                value={body.out_of_scope}
                onChange={(event) =>
                  updateText("out_of_scope", event.target.value)
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-out-of-scope"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">Escalation policy</span>
              <textarea
                value={body.escalation_policy}
                onChange={(event) =>
                  updateText("escalation_policy", event.target.value)
                }
                className={TEXTAREA_CLASS}
                data-testid="contract-escalation-policy"
              />
            </label>
          </div>
        </div>

        {state.kind === "error" ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            data-testid="contract-error"
          >
            {state.message}
          </p>
        ) : state.kind === "saved" ? (
          <p
            className="rounded-md border border-success/40 bg-success/10 px-3 py-2 text-sm text-success"
            data-testid="contract-success"
          >
            {state.message}
          </p>
        ) : null}

        <div className="sticky bottom-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-md border bg-card/95 p-3 shadow-sm backdrop-blur">
          <p className="text-xs text-muted-foreground">
            Contract hash:{" "}
            <code data-testid="contract-hash">
              {loadedCommitment
                ? document.content_hash.slice(0, 12)
                : "not loaded"}
            </code>
          </p>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || backendUnavailable}
              className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
              data-testid="contract-save-draft"
            >
              {state.kind === "saving" ? "Saving..." : "Save draft"}
            </button>
            <button
              type="button"
              disabled={missing.length > 0 || busy || backendUnavailable}
              onClick={handleAccept}
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="contract-accept"
            >
              {state.kind === "accepting" ? "Accepting..." : "Accept contract"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
