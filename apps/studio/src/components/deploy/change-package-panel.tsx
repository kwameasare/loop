"use client";

import { useState } from "react";
import { FileCheck2, LockKeyhole, PackageCheck } from "lucide-react";

import {
  type ChangePackage,
  type ChangePackageGenerateInput,
  buildLocalChangePackage,
  generateChangePackage as defaultGenerateChangePackage,
  submitChangePackage as defaultSubmitChangePackage,
} from "@/lib/change-package";
import { cn } from "@/lib/utils";

interface ChangePackagePanelProps {
  agentId: string;
  initialPackage?: ChangePackage | null;
  generateChangePackage?: (
    agentId: string,
    input: ChangePackageGenerateInput,
  ) => Promise<ChangePackage>;
  submitChangePackage?: (
    agentId: string,
    packageId: string,
  ) => Promise<ChangePackage>;
}

type PanelState =
  | { kind: "idle" }
  | { kind: "generating" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

const STATUS_CLASS: Record<string, string> = {
  draft: "border-border bg-muted text-muted-foreground",
  generated: "border-info/40 bg-info/10 text-info",
  submitted: "border-warning/40 bg-warning/10 text-warning",
  stale: "border-destructive/40 bg-destructive/10 text-destructive",
  approved: "border-success/40 bg-success/10 text-success",
  deployable: "border-success/40 bg-success/10 text-success",
  deployed: "border-success/40 bg-success/10 text-success",
};

function evidenceEntries(
  changePackage: ChangePackage,
): Array<[string, string]> {
  return Object.entries(changePackage.evidence).filter(([, value]) => value);
}

function semanticSummary(item: Record<string, unknown>, index: number): string {
  const dimension =
    typeof item.dimension === "string" ? item.dimension : `diff ${index + 1}`;
  const summary =
    typeof item.summary === "string" ? item.summary : "Evidence-backed change.";
  return `${dimension}: ${summary}`;
}

export function ChangePackagePanel({
  agentId,
  initialPackage,
  generateChangePackage = defaultGenerateChangePackage,
  submitChangePackage = defaultSubmitChangePackage,
}: ChangePackagePanelProps) {
  const [changePackage, setChangePackage] = useState<ChangePackage>(
    initialPackage ?? buildLocalChangePackage(agentId),
  );
  const [state, setState] = useState<PanelState>({ kind: "idle" });
  const busy = state.kind === "generating" || state.kind === "submitting";
  const hasGenerated = changePackage.status !== "draft";
  const canSubmit = changePackage.status === "generated" && !busy;

  async function handleGenerate() {
    setState({ kind: "generating" });
    try {
      const generated = await generateChangePackage(agentId, {
        branch_id: changePackage.branch_id,
        from_version_id: changePackage.from_version_id,
        to_version_id:
          changePackage.to_version_id === "draft"
            ? "candidate-v1"
            : changePackage.to_version_id,
        target_environment: "production",
        summary:
          changePackage.status === "draft"
            ? "Generate preflight evidence for the current draft."
            : changePackage.summary,
        eval_results_ref: changePackage.eval_results_ref,
        replay_results_ref: changePackage.replay_results_ref,
        rollback_target_version_id:
          changePackage.rollback_target_version_id === "none"
            ? "last-known-safe"
            : changePackage.rollback_target_version_id,
      });
      setChangePackage(generated);
      setState({ kind: "idle" });
    } catch (error) {
      setState({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to generate Change Package.",
      });
    }
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    setState({ kind: "submitting" });
    try {
      const submitted = await submitChangePackage(agentId, changePackage.id);
      setChangePackage(submitted);
      setState({ kind: "idle" });
    } catch (error) {
      setState({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to submit Change Package.",
      });
    }
  }

  return (
    <section
      className="space-y-4 rounded-md border bg-card p-5"
      data-testid="change-package-panel"
      aria-labelledby="change-package-heading"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <PackageCheck className="h-4 w-4" aria-hidden />
            Preflight
          </div>
          <h2
            id="change-package-heading"
            className="mt-2 text-xl font-semibold"
          >
            Change Package
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Immutable promotion evidence for approvers. It links the current
            Commitment Document, semantic diff, evals, replay, cost, latency,
            channels, rollback target, and required approvals.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={busy}
            className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
            data-testid="change-package-generate"
          >
            {state.kind === "generating"
              ? "Generating..."
              : "Generate preflight"}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="change-package-submit"
          >
            {state.kind === "submitting"
              ? "Submitting..."
              : "Submit for approval"}
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Status
          </p>
          <span
            className={cn(
              "mt-2 inline-flex rounded-md border px-2 py-0.5 text-xs font-medium",
              STATUS_CLASS[changePackage.status] ?? STATUS_CLASS.draft,
            )}
            data-testid="change-package-status"
          >
            {changePackage.status}
          </span>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Commitment
          </p>
          <p
            className="mt-2 font-mono text-xs"
            data-testid="change-package-commitment"
          >
            {changePackage.commitment_document_id} v
            {changePackage.commitment_document_version}
          </p>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Hash
          </p>
          <p
            className="mt-2 font-mono text-xs"
            data-testid="change-package-hash"
          >
            {changePackage.content_hash.slice(0, 12)}
          </p>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Rollback
          </p>
          <p className="mt-2 text-sm" data-testid="change-package-rollback">
            {changePackage.rollback_target_version_id}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-md border bg-background p-4">
          <div className="flex items-start gap-2">
            <FileCheck2 className="mt-0.5 h-4 w-4 text-info" aria-hidden />
            <div>
              <h3 className="text-sm font-semibold">30-second summary</h3>
              <p className="mt-2 text-sm" data-testid="change-package-summary">
                {changePackage.summary}
              </p>
            </div>
          </div>
          <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Eval impact
              </dt>
              <dd className="mt-1 font-mono text-xs">
                {changePackage.eval_results_ref}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Replay impact
              </dt>
              <dd className="mt-1 font-mono text-xs">
                {changePackage.replay_results_ref}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Cost
              </dt>
              <dd className="mt-1">{changePackage.cost_summary}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Latency
              </dt>
              <dd className="mt-1">{changePackage.latency_summary}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-md border bg-background p-4">
          <div className="flex items-start gap-2">
            <LockKeyhole className="mt-0.5 h-4 w-4 text-warning" aria-hidden />
            <div>
              <h3 className="text-sm font-semibold">Approval requirements</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                Approvers review this package, not raw implementation details.
              </p>
            </div>
          </div>
          <ul className="mt-3 space-y-2">
            {changePackage.required_approvals.length ? (
              changePackage.required_approvals.map((approval) => (
                <li
                  key={approval.id}
                  className="rounded-md border bg-card p-2 text-sm"
                  data-testid={`change-package-approval-${approval.id}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{approval.role}</span>
                    <span className="text-xs text-muted-foreground">
                      {approval.required ? "required" : "optional"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {approval.reason}
                  </p>
                </li>
              ))
            ) : (
              <li className="text-sm text-muted-foreground">
                Generate preflight to compute approval requirements.
              </li>
            )}
          </ul>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-md border bg-background p-4">
          <h3 className="text-sm font-semibold">Semantic diff</h3>
          <ul
            className="mt-3 space-y-2 text-sm"
            data-testid="change-package-diff"
          >
            {changePackage.semantic_diff.length ? (
              changePackage.semantic_diff.map((item, index) => (
                <li key={index} className="rounded-md border bg-card p-2">
                  {semanticSummary(item, index)}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">
                Generate preflight to summarize behavior, tool, knowledge,
                memory, channel, and budget changes.
              </li>
            )}
          </ul>
        </article>

        <article className="rounded-md border bg-background p-4">
          <h3 className="text-sm font-semibold">Evidence links</h3>
          <ul
            className="mt-3 space-y-2 text-sm"
            data-testid="change-package-evidence"
          >
            {hasGenerated && evidenceEntries(changePackage).length ? (
              evidenceEntries(changePackage).map(([key, value]) => (
                <li
                  key={key}
                  className="flex items-center justify-between gap-3"
                >
                  <span className="text-muted-foreground">{key}</span>
                  <code className="break-all text-xs">{value}</code>
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">
                No evidence pack exists until preflight runs.
              </li>
            )}
          </ul>
        </article>
      </div>

      <p className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        Package ID: <code>{changePackage.id}</code> · Evidence pack:{" "}
        <code>{changePackage.evidence_pack_id}</code>
      </p>

      {state.kind === "error" ? (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="change-package-error"
        >
          {state.message}
        </p>
      ) : null}
    </section>
  );
}
