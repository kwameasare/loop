"use client";

import { useMemo, useState } from "react";

import {
  countBlocking,
  diffsBy,
  summarizeReplay,
  type DiffEntry,
  type DiffMode,
  type ImportLineage,
  type ParityReadiness,
  type ParityReplayCase,
  type RepairSuggestion,
} from "@/lib/migration-parity";

const MODES: readonly DiffMode[] = ["structure", "behavior", "cost", "risk"];

const STATUS_TONE: Record<string, string> = {
  ok: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pass: "bg-emerald-50 text-emerald-700 border-emerald-200",
  improve: "bg-sky-50 text-sky-700 border-sky-200",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  advisory: "bg-amber-50 text-amber-700 border-amber-200",
  regress: "bg-rose-50 text-rose-700 border-rose-200",
  blocking: "bg-rose-50 text-rose-700 border-rose-200",
  error: "bg-rose-50 text-rose-700 border-rose-200",
  skipped: "bg-slate-50 text-slate-500 border-slate-200",
};

function pill(status: string): string {
  return (
    "inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded " +
    (STATUS_TONE[status] ?? "bg-slate-50 text-slate-600 border-slate-200")
  );
}

export interface ParityHarnessProps {
  lineage: ImportLineage;
  readiness: ParityReadiness;
  diffs: readonly DiffEntry[];
  replay: readonly ParityReplayCase[];
  repairs: readonly RepairSuggestion[];
  /**
   * Called when the operator accepts a grounded repair suggestion. The
   * caller owns the actual patch application; this surface only emits
   * the user intent. Defaults to a no-op so the harness renders without
   * a wire-up.
   */
  onAcceptRepair?: (repair: RepairSuggestion) => void;
}

export function ParityHarness({
  lineage,
  readiness,
  diffs,
  replay,
  repairs,
  onAcceptRepair,
}: ParityHarnessProps): JSX.Element {
  const [mode, setMode] = useState<DiffMode>("structure");
  const [acceptedRepairs, setAcceptedRepairs] = useState<Record<string, boolean>>(
    {},
  );

  const filteredDiffs = useMemo(() => diffsBy(diffs, mode), [diffs, mode]);
  const replaySummary = useMemo(() => summarizeReplay(replay), [replay]);
  const blockingCount = countBlocking(diffs);

  return (
    <div data-testid="parity-harness" className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-xl font-semibold">Parity harness</h2>
        <p className="text-sm text-slate-600">
          Lineage, diffs, replay, and grounded repair for the imported Botpress
          archive.
        </p>
      </header>

      <section
        data-testid="parity-readiness"
        className="grid gap-2 md:grid-cols-4 border rounded p-3"
      >
        <Stat label="Readiness" value={`${readiness.overallScore}%`} />
        <Stat
          label="Parity"
          value={`${readiness.parityPassing}/${readiness.parityTotal}`}
        />
        <Stat
          label="Blocking diffs"
          value={String(blockingCount)}
          tone={blockingCount > 0 ? "blocking" : "ok"}
        />
        <Stat label="Advisories" value={String(readiness.advisoryCount)} tone="advisory" />
      </section>

      <section data-testid="parity-lineage" className="border rounded p-3 space-y-2">
        <header className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Import lineage</h3>
          <div className="text-xs text-slate-500">
            <span className="font-mono">{lineage.archive}</span> ·{" "}
            <span className="font-mono">{lineage.archiveSha.slice(0, 23)}…</span>
          </div>
        </header>
        <ol className="space-y-1">
          {lineage.steps.map((step) => (
            <li
              key={step.id}
              data-testid={`lineage-step-${step.id}`}
              className="flex items-start justify-between gap-3 text-sm"
            >
              <div>
                <div className="font-medium">{step.label}</div>
                <div className="text-slate-600">{step.detail}</div>
                <div className="text-xs text-slate-400">
                  evidence: {step.evidenceRef}
                </div>
              </div>
              <span className={pill(step.status)}>{step.status}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-2">
        <nav data-testid="parity-tablist" role="tablist" className="flex gap-1 border-b">
          {MODES.map((m) => {
            const active = mode === m;
            return (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={active}
                data-testid={`parity-tab-${m}`}
                onClick={() => setMode(m)}
                className={
                  "px-3 py-1.5 text-sm capitalize border-b-2 -mb-px " +
                  (active
                    ? "border-slate-900 text-slate-900"
                    : "border-transparent text-slate-500 hover:text-slate-800")
                }
              >
                {m}
              </button>
            );
          })}
        </nav>
        <ul data-testid={`parity-pane-${mode}`} className="space-y-2">
          {filteredDiffs.length === 0 && (
            <li
              data-testid="parity-empty"
              className="text-sm text-slate-500 border rounded p-3"
            >
              No {mode} diffs.
            </li>
          )}
          {filteredDiffs.map((d) => (
            <li
              key={d.id}
              data-testid={`diff-row-${d.id}`}
              className="border rounded p-3 space-y-1"
            >
              <div className="flex items-center justify-between">
                <div className="font-medium text-sm">
                  <span className="font-mono">{d.sourcePath}</span>
                  {" → "}
                  <span className="font-mono">{d.targetPath}</span>
                </div>
                <span className={pill(d.severity)}>{d.severity}</span>
              </div>
              <div className="text-sm text-slate-600">{d.summary}</div>
              {d.delta && (
                <div className="text-xs text-slate-500">delta: {d.delta}</div>
              )}
              <div className="text-xs text-slate-400">evidence: {d.evidenceRef}</div>
            </li>
          ))}
        </ul>
      </section>

      <section
        data-testid="parity-replay"
        className="border rounded p-3 space-y-2"
      >
        <header className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Parity replay</h3>
          <div className="text-xs text-slate-500">
            {replaySummary.pass} pass · {replaySummary.regress} regress ·{" "}
            {replaySummary.improve} improve · {replaySummary.skipped} skipped
          </div>
        </header>
        <ul className="space-y-1">
          {replay.map((c) => (
            <li
              key={c.id}
              data-testid={`replay-row-${c.id}`}
              className="flex items-start justify-between gap-3 text-sm"
            >
              <div>
                <div className="font-medium">{c.transcript}</div>
                <div className="text-slate-600 text-xs">
                  expected: <span className="font-mono">{c.expectedTarget}</span>{" "}
                  · observed: <span className="font-mono">{c.observedTarget}</span>
                </div>
                <div className="text-xs text-slate-400">evidence: {c.evidenceRef}</div>
              </div>
              <span className={pill(c.status)}>{c.status}</span>
            </li>
          ))}
        </ul>
      </section>

      <section
        data-testid="parity-repairs"
        className="border rounded p-3 space-y-2"
      >
        <h3 className="text-sm font-medium">Grounded repair suggestions</h3>
        {repairs.length === 0 && (
          <p className="text-sm text-slate-500">No repairs proposed.</p>
        )}
        <ul className="space-y-2">
          {repairs.map((r) => {
            const accepted = !!acceptedRepairs[r.id];
            return (
              <li
                key={r.id}
                data-testid={`repair-row-${r.id}`}
                className="border rounded p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">{r.patchSummary}</div>
                    <div className="text-sm text-slate-600">{r.rationale}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      grounded in: {r.groundingRef} · confidence: {r.confidence}
                    </div>
                  </div>
                  {accepted ? (
                    <span
                      className={pill("ok")}
                      data-testid={`repair-accepted-${r.id}`}
                    >
                      accepted
                    </span>
                  ) : (
                    <button
                      type="button"
                      data-testid={`repair-accept-${r.id}`}
                      onClick={() => {
                        setAcceptedRepairs((prev) => ({ ...prev, [r.id]: true }));
                        onAcceptRepair?.(r);
                      }}
                      className="px-2 py-1 text-xs border rounded hover:bg-slate-50"
                    >
                      Accept
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}): JSX.Element {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="flex items-center gap-2">
        <div className="text-lg font-semibold">{value}</div>
        {tone && <span className={pill(tone)}>{tone}</span>}
      </div>
    </div>
  );
}
