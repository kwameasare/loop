"use client";

import { useState } from "react";
import { History, ShieldAlert, UserRoundCheck } from "lucide-react";

import {
  transferAgentOwner as defaultTransferAgentOwner,
  type AgentHandoffModel,
  type HandoffRisk,
} from "@/lib/agent-handoff";
import { cn } from "@/lib/utils";

interface AgentHistoryWalkthroughProps {
  agentId: string;
  initialModel: AgentHandoffModel;
  transferAgentOwner?: typeof defaultTransferAgentOwner;
}

const RISK_CLASS: Record<string, string> = {
  blocking: "border-destructive/40 bg-destructive/10 text-destructive",
  advisory: "border-warning/40 bg-warning/10 text-warning-foreground",
  info: "border-info/40 bg-info/10 text-info-foreground",
};

function riskIds(risks: HandoffRisk[]): string[] {
  return risks.map((risk) => risk.id);
}

export function AgentHistoryWalkthrough({
  agentId,
  initialModel,
  transferAgentOwner = defaultTransferAgentOwner,
}: AgentHistoryWalkthroughProps) {
  const [model, setModel] = useState(initialModel);
  const [newOwner, setNewOwner] = useState(
    initialModel.owner_user_id || "new-owner@example.com",
  );
  const [backupOwner, setBackupOwner] = useState(
    initialModel.backup_owner_user_id || "",
  );
  const [reason, setReason] = useState("Planned ownership rotation");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleTransfer() {
    setBusy(true);
    setNotice(null);
    try {
      const next = await transferAgentOwner(
        agentId,
        {
          new_owner_user_id: newOwner,
          backup_owner_user_id: backupOwner,
          reason,
          acknowledged_risk_ids: riskIds(model.open_risks),
        },
        { fallbackModel: model },
      );
      setModel(next);
      setNotice(
        "Ownership transfer recorded and history walkthrough refreshed.",
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not transfer owner.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="space-y-5"
      data-testid="agent-history-walkthrough"
      aria-labelledby="agent-history-heading"
    >
      <header className="rounded-md border bg-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Handoff and continuity
        </p>
        <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 id="agent-history-heading" className="text-lg font-semibold">
              New owners should understand this agent without oral tradition.
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              The walkthrough collects commitments, behavior versions, Change
              Packages, approvals, deployments, incidents, and open risks into
              one transfer surface.
            </p>
          </div>
          <div className="rounded-md border bg-background p-3 text-sm">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Current owner
            </p>
            <p className="mt-1 font-medium" data-testid="handoff-current-owner">
              {model.owner_user_id || "Unassigned"}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Backup: {model.backup_owner_user_id || "None assigned"}
            </p>
          </div>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-md border bg-card p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" aria-hidden />
            <h3 className="text-sm font-semibold">
              Open risks before transfer
            </h3>
          </div>
          {model.open_risks.length ? (
            <ul className="mt-3 space-y-2" data-testid="handoff-open-risks">
              {model.open_risks.map((risk) => (
                <li
                  key={risk.id}
                  className="rounded-md border bg-background p-3"
                  data-testid={`handoff-risk-${risk.id}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">{risk.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {risk.detail}
                      </p>
                      <p className="mt-2 font-mono text-xs text-muted-foreground">
                        {risk.evidence_ref}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "rounded-md border px-2 py-0.5 text-xs font-medium",
                        RISK_CLASS[risk.severity] ?? RISK_CLASS.info,
                      )}
                    >
                      {risk.severity}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 rounded-md border bg-background p-3 text-sm text-muted-foreground">
              No open handoff risks are currently reported.
            </p>
          )}
        </section>

        <section className="rounded-md border bg-card p-4">
          <div className="flex items-center gap-2">
            <UserRoundCheck className="h-4 w-4" aria-hidden />
            <h3 className="text-sm font-semibold">Transfer ownership</h3>
          </div>
          <div className="mt-3 space-y-3">
            <label className="block text-sm">
              <span className="font-medium">New owner</span>
              <input
                value={newOwner}
                onChange={(event) => setNewOwner(event.target.value)}
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                data-testid="handoff-new-owner"
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium">Backup owner</span>
              <input
                value={backupOwner}
                onChange={(event) => setBackupOwner(event.target.value)}
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                data-testid="handoff-backup-owner"
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium">Reason</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                className="mt-1 min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm"
                data-testid="handoff-reason"
              />
            </label>
            <button
              type="button"
              onClick={handleTransfer}
              disabled={busy || !newOwner.trim()}
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="handoff-transfer"
            >
              {busy ? "Transferring..." : "Transfer owner"}
            </button>
          </div>
          {notice ? (
            <p
              className="mt-3 rounded-md border border-info/40 bg-info/5 p-3 text-sm text-muted-foreground"
              role="status"
              data-testid="handoff-notice"
            >
              {notice}
            </p>
          ) : null}
        </section>
      </div>

      <section className="rounded-md border bg-card p-4">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4" aria-hidden />
          <h3 className="text-sm font-semibold">History walkthrough</h3>
        </div>
        <ol className="mt-3 grid gap-3 md:grid-cols-2">
          {model.walkthrough_sections.map((section) => (
            <li
              key={section.id}
              className="rounded-md border bg-background p-3"
              data-testid={`walkthrough-section-${section.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{section.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {section.summary}
                  </p>
                </div>
                <span className="rounded-md border bg-card px-2 py-0.5 text-xs font-medium">
                  {section.count}
                </span>
              </div>
              {section.evidence_refs.length ? (
                <ul className="mt-3 space-y-1">
                  {section.evidence_refs.slice(0, 3).map((ref) => (
                    <li
                      key={ref}
                      className="truncate font-mono text-xs text-muted-foreground"
                    >
                      {ref}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-xs text-muted-foreground">
                  No evidence objects yet.
                </p>
              )}
            </li>
          ))}
        </ol>
      </section>

      {model.transfers.length ? (
        <section className="rounded-md border bg-card p-4">
          <h3 className="text-sm font-semibold">Transfer record</h3>
          <ul className="mt-3 space-y-2" data-testid="handoff-transfers">
            {model.transfers.map((transfer) => (
              <li
                key={transfer.id}
                className="rounded-md border bg-background p-3"
              >
                <p className="text-sm">
                  {transfer.previous_owner_user_id || "Unassigned"} {"->"}{" "}
                  {transfer.new_owner_user_id}
                </p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {transfer.history_walkthrough_id}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
