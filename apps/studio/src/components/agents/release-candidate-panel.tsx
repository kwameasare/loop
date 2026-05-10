"use client";

import { useMemo, useState } from "react";
import { GitBranch, PackageCheck, ShieldCheck } from "lucide-react";

import {
  approveReleaseCandidate as defaultApproveReleaseCandidate,
  createAgentBranch as defaultCreateAgentBranch,
  createAgentChangeSet as defaultCreateAgentChangeSet,
  createReleaseCandidate as defaultCreateReleaseCandidate,
  markChangeSetReadyForReview as defaultMarkChangeSetReadyForReview,
  markChangeSetReadyForTests as defaultMarkChangeSetReadyForTests,
  type AgentBranch,
  type AgentChangeSet,
  type AgentReleaseCandidate,
  type AgentWorkflow,
  type GateStatus,
  updateReleaseCandidateGate as defaultUpdateReleaseCandidateGate,
} from "@/lib/agent-workflow";
import { cn } from "@/lib/utils";

interface ReleaseCandidatePanelProps {
  agentId: string;
  initialWorkflow: AgentWorkflow;
  createBranch?: typeof defaultCreateAgentBranch;
  createChangeSet?: typeof defaultCreateAgentChangeSet;
  markReadyForTests?: typeof defaultMarkChangeSetReadyForTests;
  markReadyForReview?: typeof defaultMarkChangeSetReadyForReview;
  createReleaseCandidate?: typeof defaultCreateReleaseCandidate;
  approveReleaseCandidate?: typeof defaultApproveReleaseCandidate;
  updateReleaseCandidateGate?: typeof defaultUpdateReleaseCandidateGate;
}

type BusyState =
  | "idle"
  | "branch"
  | "change-set"
  | "tests"
  | "review"
  | "release-candidate"
  | "gate"
  | "approval";

const STATUS_CLASS: Record<string, string> = {
  active: "border-info/40 bg-info/5 text-info",
  draft: "border-muted bg-muted text-muted-foreground",
  ready_for_tests: "border-warning/40 bg-warning/5 text-warning",
  ready_for_review: "border-info/40 bg-info/5 text-info",
  converted_to_release_candidate: "border-success/40 bg-success/5 text-success",
  testing: "border-warning/40 bg-warning/5 text-warning",
  blocked: "border-destructive/40 bg-destructive/5 text-destructive",
  ready_for_approval: "border-info/40 bg-info/5 text-info",
  approved: "border-success/40 bg-success/5 text-success",
  deployable: "border-success/40 bg-success/5 text-success",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "rounded-md border px-2 py-0.5 text-xs font-medium",
        STATUS_CLASS[status] ?? "border-border bg-muted text-muted-foreground",
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

function latest<T extends { updated_at: string }>(items: T[]): T | null {
  return (
    [...items].sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0] ??
    null
  );
}

export function ReleaseCandidatePanel({
  agentId,
  initialWorkflow,
  createBranch = defaultCreateAgentBranch,
  createChangeSet = defaultCreateAgentChangeSet,
  markReadyForTests = defaultMarkChangeSetReadyForTests,
  markReadyForReview = defaultMarkChangeSetReadyForReview,
  createReleaseCandidate = defaultCreateReleaseCandidate,
  approveReleaseCandidate = defaultApproveReleaseCandidate,
  updateReleaseCandidateGate = defaultUpdateReleaseCandidateGate,
}: ReleaseCandidatePanelProps) {
  const [workflow, setWorkflow] = useState(initialWorkflow);
  const [busy, setBusy] = useState<BusyState>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const branch = useMemo(() => latest(workflow.branches), [workflow.branches]);
  const changeSet = useMemo(
    () => latest(workflow.change_sets),
    [workflow.change_sets],
  );
  const releaseCandidate = useMemo(
    () => latest(workflow.release_candidates),
    [workflow.release_candidates],
  );
  const degradedReason = workflow.degraded_reason;
  const workflowUnavailable = Boolean(degradedReason);

  const canCreateChangeSet = Boolean(branch) && !changeSet;
  const canMarkReadyForTests = changeSet?.status === "draft";
  const canMarkReadyForReview = changeSet?.status === "ready_for_tests";
  const canCreateReleaseCandidate = changeSet?.status === "ready_for_review";
  const requiredGatesSatisfied = Boolean(
    releaseCandidate?.readiness.length &&
      releaseCandidate.readiness.every((gate) => gate.status === "passed"),
  );
  const hasFailedGate = Boolean(
    releaseCandidate?.readiness.some((gate) => gate.status === "failed"),
  );

  function upsertBranch(next: AgentBranch) {
    setWorkflow((current) => ({
      ...current,
      branches: [
        next,
        ...current.branches.filter((item) => item.id !== next.id),
      ],
    }));
  }

  function upsertChangeSet(next: AgentChangeSet) {
    setWorkflow((current) => ({
      ...current,
      change_sets: [
        next,
        ...current.change_sets.filter((item) => item.id !== next.id),
      ],
    }));
  }

  function upsertReleaseCandidate(next: AgentReleaseCandidate) {
    setWorkflow((current) => ({
      ...current,
      release_candidates: [
        next,
        ...current.release_candidates.filter((item) => item.id !== next.id),
      ],
    }));
  }

  async function handleCreateBranch() {
    setBusy("branch");
    setNotice(null);
    try {
      const next = await createBranch(agentId, {
        name: "draft/current-agent-work",
        base_version_id: "production",
      });
      upsertBranch(next);
      setNotice("Branch created. Add a change set before tests.");
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not create branch.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleCreateChangeSet() {
    if (!branch) return;
    setBusy("change-set");
    setNotice(null);
    try {
      const next = await createChangeSet(agentId, {
        branch_id: branch.id,
        name: "Fix observed behavior",
        summary:
          "Collect behavior, tool, knowledge, memory, channel, and eval changes.",
        source_type: "manual_edit",
        source_refs: ["studio/manual"],
        changed_objects: [
          {
            type: "behavior",
            id: "behavior.current",
            summary: "Draft behavior change collected for tests.",
          },
        ],
      });
      upsertChangeSet(next);
      setNotice("Change set created. Run required tests next.");
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not create change set.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleReadyForTests() {
    if (!changeSet) return;
    setBusy("tests");
    setNotice(null);
    try {
      const next = await markReadyForTests(agentId, changeSet.id, {
        fallbackChangeSet: changeSet,
      });
      upsertChangeSet(next);
      setNotice("Change set is ready for required tests.");
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not update change set.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleReadyForReview() {
    if (!changeSet) return;
    setBusy("review");
    setNotice(null);
    try {
      const next = await markReadyForReview(
        agentId,
        changeSet.id,
        {
          eval_results_ref: "eval/run/current-agent-work/green",
          required_eval_suites: ["core-regression"],
          passed: true,
        },
        { fallbackChangeSet: changeSet },
      );
      upsertChangeSet(next);
      setNotice("Tests passed. A release candidate can now be created.");
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not record tests.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleCreateReleaseCandidate() {
    if (!changeSet) return;
    setBusy("release-candidate");
    setNotice(null);
    try {
      const next = await createReleaseCandidate(agentId, changeSet.id, {
        required_eval_suites: changeSet.required_eval_suites.length
          ? changeSet.required_eval_suites
          : ["core-regression"],
        required_approvals: ["owner", "compliance"],
      });
      upsertReleaseCandidate(next);
      upsertChangeSet({
        ...changeSet,
        status: "converted_to_release_candidate",
      });
      setNotice("Release candidate created with immutable candidate version.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not create release candidate.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleGateUpdate(gateId: string, status: GateStatus) {
    if (!releaseCandidate) return;
    setBusy("gate");
    setNotice(null);
    try {
      const gate = releaseCandidate.readiness.find((item) => item.id === gateId);
      const next = await updateReleaseCandidateGate(
        agentId,
        releaseCandidate.id,
        {
          gate_id: gateId,
          status,
          evidence_ref:
            status === "passed"
              ? `manual/${gateId}/passed`
              : `manual/${gateId}/failed`,
          message:
            status === "passed"
              ? `${gate?.label ?? gateId} passed with reviewer evidence.`
              : `${gate?.label ?? gateId} failed and blocks approval.`,
        },
        { fallbackReleaseCandidate: releaseCandidate },
      );
      upsertReleaseCandidate(next);
      setNotice(
        status === "passed"
          ? `Gate passed. Release candidate is ${next.status}.`
          : "Gate failed. Approval is blocked until this is fixed.",
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not update readiness gate.",
      );
    } finally {
      setBusy("idle");
    }
  }

  async function handleApprove(approvalId: string) {
    if (!releaseCandidate) return;
    setBusy("approval");
    setNotice(null);
    try {
      const next = await approveReleaseCandidate(
        agentId,
        releaseCandidate.id,
        {
          approval_id: approvalId,
          comment: "Reviewed release candidate evidence.",
        },
        { fallbackReleaseCandidate: releaseCandidate },
      );
      upsertReleaseCandidate(next);
      setNotice(`Approval recorded. Release candidate is ${next.status}.`);
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not approve release candidate.",
      );
    } finally {
      setBusy("idle");
    }
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="release-candidate-panel"
      aria-labelledby="release-candidate-heading"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold">
              <GitBranch className="h-4 w-4" aria-hidden />
              Branch to release candidate
            </p>
            <h2
              id="release-candidate-heading"
              className="mt-1 text-lg font-semibold"
            >
              Draft work becomes reviewable evidence before preflight
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Edits collect in a Change Set, tests convert the work into a
              Release Candidate, and only deployable candidates should feed
              Change Package preflight.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50 disabled:opacity-50"
              disabled={workflowUnavailable || busy !== "idle"}
              onClick={handleCreateBranch}
              data-testid="workflow-create-branch"
            >
              {busy === "branch"
                ? "Creating..."
                : branch
                  ? "New branch"
                  : "Create branch"}
            </button>
            <button
              type="button"
              className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50 disabled:opacity-50"
              disabled={
                workflowUnavailable || !canCreateChangeSet || busy !== "idle"
              }
              onClick={handleCreateChangeSet}
              data-testid="workflow-create-change-set"
            >
              Create change set
            </button>
          </div>
        </div>

        {degradedReason ? (
          <p
            className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
            data-testid="workflow-degraded"
            role="status"
          >
            Release workflow is unavailable. {degradedReason}
          </p>
        ) : null}

        <div className="grid gap-3 lg:grid-cols-3">
          <article
            className="rounded-md border bg-background p-3"
            data-testid="workflow-branch"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">Branch</h3>
              {branch ? <StatusBadge status={branch.status} /> : null}
            </div>
            {branch ? (
              <dl className="mt-3 space-y-2 text-sm">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                    Name
                  </dt>
                  <dd>{branch.name}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                    Base version
                  </dt>
                  <dd>{branch.base_version_id}</dd>
                </div>
              </dl>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                No branch has collected work for this agent.
              </p>
            )}
          </article>

          <article
            className="rounded-md border bg-background p-3"
            data-testid="workflow-change-set"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">Change Set</h3>
              {changeSet ? <StatusBadge status={changeSet.status} /> : null}
            </div>
            {changeSet ? (
              <>
                <p className="mt-3 text-sm font-medium">{changeSet.name}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {changeSet.summary}
                </p>
                <p className="mt-2 font-mono text-xs text-muted-foreground">
                  {changeSet.eval_results_ref ?? "tests not recorded"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-muted/50 disabled:opacity-50"
                    disabled={
                      workflowUnavailable || !canMarkReadyForTests || busy !== "idle"
                    }
                    onClick={handleReadyForTests}
                    data-testid="workflow-ready-tests"
                  >
                    Ready for tests
                  </button>
                  <button
                    type="button"
                    className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-muted/50 disabled:opacity-50"
                    disabled={
                      workflowUnavailable ||
                      !canMarkReadyForReview ||
                      busy !== "idle"
                    }
                    onClick={handleReadyForReview}
                    data-testid="workflow-ready-review"
                  >
                    Record passing tests
                  </button>
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                Create a branch-local change set before tests or preflight.
              </p>
            )}
          </article>

          <article
            className="rounded-md border bg-background p-3"
            data-testid="workflow-release-candidate"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="flex items-center gap-2 text-sm font-semibold">
                <PackageCheck className="h-4 w-4" aria-hidden />
                Release Candidate
              </h3>
              {releaseCandidate ? (
                <StatusBadge status={releaseCandidate.status} />
              ) : null}
            </div>
            {releaseCandidate ? (
              <>
                <p className="mt-3 font-mono text-xs text-muted-foreground">
                  candidate version {releaseCandidate.candidate_version_id}
                </p>
                {!requiredGatesSatisfied ? (
                  <p
                    className={cn(
                      "mt-3 rounded-md border p-2 text-xs",
                      hasFailedGate
                        ? "border-destructive/40 bg-destructive/5 text-destructive"
                        : "border-warning/40 bg-warning/5 text-warning",
                    )}
                    data-testid="workflow-gate-blocker"
                  >
                    {hasFailedGate
                      ? "A failed readiness gate blocks approvals until the gate passes again."
                      : "All required readiness gates must pass before approvals can be recorded."}
                  </p>
                ) : null}
                <ul className="mt-3 space-y-2 text-sm">
                  {releaseCandidate.readiness.map((gate) => (
                    <li key={gate.id} className="rounded-md border bg-card p-2">
                      <div className="flex items-center justify-between gap-2">
                        <span>{gate.label}</span>
                        <StatusBadge status={gate.status} />
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {gate.evidence_ref || gate.message}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-md border border-success/40 px-2 py-1 text-xs font-medium text-success hover:bg-success/10 disabled:opacity-50"
                          disabled={
                            workflowUnavailable ||
                            busy !== "idle" ||
                            gate.status === "passed"
                          }
                          onClick={() => handleGateUpdate(gate.id, "passed")}
                          data-testid={`workflow-gate-pass-${gate.id}`}
                        >
                          Mark pass
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-destructive/40 px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                          disabled={
                            workflowUnavailable ||
                            busy !== "idle" ||
                            gate.status === "failed"
                          }
                          onClick={() => handleGateUpdate(gate.id, "failed")}
                          data-testid={`workflow-gate-fail-${gate.id}`}
                        >
                          Mark fail
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 space-y-2">
                  {releaseCandidate.required_approvals.map((approval) => (
                    <div
                      key={approval.id}
                      className="flex items-center justify-between gap-2 rounded-md border bg-card p-2 text-sm"
                    >
                      <span className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4" aria-hidden />
                        {approval.id}
                      </span>
                      <button
                        type="button"
                        className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-muted/50 disabled:opacity-50"
                        disabled={
                          workflowUnavailable ||
                          !requiredGatesSatisfied ||
                          approval.satisfied ||
                          busy !== "idle"
                        }
                        onClick={() => handleApprove(approval.id)}
                        data-testid={`workflow-approve-${approval.id}`}
                      >
                        {approval.satisfied ? "Approved" : "Approve"}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <p className="mt-3 text-sm text-muted-foreground">
                  Release Candidate creation is locked until required tests
                  pass.
                </p>
                <button
                  type="button"
                  className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  disabled={
                    workflowUnavailable ||
                    !canCreateReleaseCandidate ||
                    busy !== "idle"
                  }
                  onClick={handleCreateReleaseCandidate}
                  data-testid="workflow-create-release-candidate"
                >
                  Create release candidate
                </button>
              </>
            )}
          </article>
        </div>

        {notice ? (
          <p
            className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
            role="status"
            data-testid="workflow-notice"
          >
            {notice}
          </p>
        ) : null}
      </div>
    </section>
  );
}
