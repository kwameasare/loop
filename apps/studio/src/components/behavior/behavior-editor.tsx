"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Code2,
  FileText,
  ListChecks,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";

import {
  ConfidenceMeter,
  DiffRibbon,
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
  BEHAVIOR_MODE_DESCRIPTION,
  BEHAVIOR_MODE_LABEL,
  type BehaviorEditorData,
  type BehaviorMode,
  type BehaviorRiskFlag,
  type BehaviorRiskLevel,
  type BehaviorSection,
  type BehaviorSentence,
  type BehaviorSentenceTelemetry,
} from "@/lib/behavior";
import { cn } from "@/lib/utils";

export interface BehaviorEditorProps {
  data: BehaviorEditorData;
}

const MODE_ORDER: BehaviorMode[] = ["plain", "policy", "config"];

const RISK_CLASS: Record<BehaviorRiskLevel, string> = {
  low: "border-info/40 bg-info/5 text-info",
  medium: "border-warning/50 bg-warning/5 text-warning",
  high: "border-destructive/40 bg-destructive/5 text-destructive",
  blocked: "border-destructive bg-destructive/10 text-destructive",
};

function ModeIcon({ mode }: { mode: BehaviorMode }) {
  if (mode === "plain") return <FileText className="h-4 w-4" aria-hidden />;
  if (mode === "policy") {
    return <ListChecks className="h-4 w-4" aria-hidden />;
  }
  return <Code2 className="h-4 w-4" aria-hidden />;
}

function riskLabel(risk: BehaviorRiskLevel): string {
  if (risk === "blocked") return "Blocked";
  return `${risk[0]?.toUpperCase() ?? ""}${risk.slice(1)} risk`;
}

function riskTone(
  risk: BehaviorRiskLevel,
): "low" | "medium" | "high" | "blocked" {
  return risk;
}

function liveBadgeTone(
  state: BehaviorEditorData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function telemetrySummary(telemetry: BehaviorSentenceTelemetry): string {
  return [
    `Cited in ${telemetry.citedOutputs7d} outputs over 7 days.`,
    `Contradicted in ${telemetry.contradictedTraces} sampled traces.`,
    `Never visibly invoked in ${telemetry.neverInvokedTurns} sampled turns.`,
    `Covered by ${telemetry.evalCases} eval cases.`,
  ].join(" ");
}

function allSentences(sections: BehaviorSection[]): BehaviorSentence[] {
  return sections.flatMap((section) => section.sentences);
}

function riskMap(flags: BehaviorRiskFlag[]): Map<string, BehaviorRiskFlag> {
  return new Map(flags.map((flag) => [flag.id, flag]));
}

function RiskBadge({ flag }: { flag: BehaviorRiskFlag }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        RISK_CLASS[flag.level],
      )}
      data-testid={`behavior-risk-${flag.id}`}
    >
      <AlertTriangle className="h-3 w-3" aria-hidden />
      {flag.label}
    </span>
  );
}

function ModeSwitcher({
  mode,
  onModeChange,
}: {
  mode: BehaviorMode;
  onModeChange: (mode: BehaviorMode) => void;
}) {
  return (
    <div
      className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,10rem),1fr))]"
      role="tablist"
      aria-label="Behavior authoring modes"
      data-testid="behavior-mode-switcher"
    >
      {MODE_ORDER.map((option) => {
        const selected = option === mode;
        return (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-pressed={selected}
            className={cn(
              "flex min-h-16 items-start gap-2 rounded-md border p-3 text-left transition-colors duration-swift ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              selected
                ? "border-primary bg-primary/5 text-foreground"
                : "bg-card hover:bg-muted/50",
            )}
            onClick={() => onModeChange(option)}
            data-testid={`behavior-mode-${option}`}
          >
            <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background">
              <ModeIcon mode={option} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">
                {BEHAVIOR_MODE_LABEL[option]}
              </span>
              <span className="mt-1 block text-xs text-muted-foreground">
                {BEHAVIOR_MODE_DESCRIPTION[option]}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function SentenceButton({
  sentence,
  risks,
  selected,
  onSelect,
}: {
  sentence: BehaviorSentence;
  risks: Map<string, BehaviorRiskFlag>;
  selected: boolean;
  onSelect: (sentenceId: string) => void;
}) {
  const sentenceRisks = sentence.riskIds
    .map((riskId) => risks.get(riskId))
    .filter((risk): risk is BehaviorRiskFlag => Boolean(risk));
  return (
    <button
      type="button"
      aria-pressed={selected}
      title={telemetrySummary(sentence.telemetry)}
      className={cn(
        "w-full rounded-md border bg-background p-3 text-left text-sm leading-6 transition-colors duration-swift ease-standard hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
        selected ? "border-primary ring-1 ring-primary/40" : "border-border",
      )}
      onMouseEnter={() => onSelect(sentence.id)}
      onFocus={() => onSelect(sentence.id)}
      onClick={() => onSelect(sentence.id)}
      data-testid={`behavior-sentence-${sentence.id}`}
    >
      <span>{sentence.text}</span>
      <span className="mt-2 flex flex-wrap gap-1">
        <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {sentence.role}
        </span>
        <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {sentence.tokenCount} tokens
        </span>
        {sentenceRisks.map((flag) => (
          <RiskBadge key={flag.id} flag={flag} />
        ))}
      </span>
    </button>
  );
}

function PlainLanguageMode({
  sections,
  risks,
  selectedSentenceId,
  onSelectSentence,
}: {
  sections: BehaviorSection[];
  risks: Map<string, BehaviorRiskFlag>;
  selectedSentenceId: string | null;
  onSelectSentence: (sentenceId: string) => void;
}) {
  return (
    <div className="space-y-4" data-testid="behavior-plain-mode">
      {sections.map((section) => (
        <section
          key={section.id}
          className="rounded-md border bg-card p-4"
          aria-labelledby={`behavior-section-${section.id}`}
        >
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3
                className="text-sm font-semibold"
                id={`behavior-section-${section.id}`}
              >
                {section.label}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {section.description}
              </p>
            </div>
            <span className="rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground">
              {section.coveragePercent}% eval coverage
            </span>
          </div>
          <div className="space-y-2">
            {section.sentences.map((sentence) => (
              <SentenceButton
                key={sentence.id}
                sentence={sentence}
                risks={risks}
                selected={sentence.id === selectedSentenceId}
                onSelect={onSelectSentence}
              />
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Diff from production: {section.diffFromProduction}
          </p>
        </section>
      ))}
    </div>
  );
}

function StructuredPolicyMode({ sections }: { sections: BehaviorSection[] }) {
  return (
    <div className="space-y-4" data-testid="behavior-policy-mode">
      {sections.map((section) => (
        <section key={section.id} className="rounded-md border bg-card p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold">{section.label}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {section.description}
              </p>
            </div>
            <span className="rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground">
              Evidence: {section.evidence}
            </span>
          </div>
          <ul className="mt-3 space-y-2">
            {section.policyRules.map((rule) => (
              <li
                key={rule}
                className="rounded-md border bg-background px-3 py-2 text-sm"
              >
                {rule}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function CodeConfigMode({ sections }: { sections: BehaviorSection[] }) {
  return (
    <div className="space-y-4" data-testid="behavior-config-mode">
      {sections.map((section) => (
        <section key={section.id} className="rounded-md border bg-card p-4">
          <div className="mb-2 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-sm font-semibold">{section.label}</h3>
            <span className="text-xs text-muted-foreground">
              Branch-ready config
            </span>
          </div>
          <pre className="overflow-auto rounded-md bg-foreground p-3 text-xs leading-5 text-background">
            <code>{section.config}</code>
          </pre>
        </section>
      ))}
    </div>
  );
}

function SentenceTelemetryPanel({
  sentence,
}: {
  sentence: BehaviorSentence | null;
}) {
  if (!sentence) {
    return (
      <StatePanel state="empty" title="No sentence selected">
        <p>No evidence yet. Select a behavior sentence to inspect telemetry.</p>
      </StatePanel>
    );
  }
  const telemetry = sentence.telemetry;
  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="behavior-sentence-telemetry"
      aria-live="polite"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Sentence telemetry
      </p>
      <p className="mt-2 text-sm font-medium">{sentence.text}</p>
      <dl className="mt-3 grid gap-2 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,9rem),1fr))]">
        <div>
          <dt className="text-muted-foreground">Cited</dt>
          <dd>{telemetry.citedOutputs7d} outputs over 7 days</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Contradicted</dt>
          <dd>{telemetry.contradictedTraces} sampled traces</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Not invoked</dt>
          <dd>{telemetry.neverInvokedTurns} sampled turns</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Covered by</dt>
          <dd>{telemetry.evalCases} eval cases</dd>
        </div>
      </dl>
      <ConfidenceMeter
        className="mt-4"
        value={Math.min(100, telemetry.evalCases * 12)}
        level={telemetry.confidence}
        label="Telemetry confidence"
        evidence={`Evidence: ${telemetry.evidence}`}
      />
    </section>
  );
}

function RiskPanel({ flags }: { flags: BehaviorRiskFlag[] }) {
  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="behavior-risk-flags"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Inline risk flags
      </p>
      {flags.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">
          No risk flags yet. Add behavior sections or run replay to gather
          evidence.
        </p>
      ) : (
        <div className="mt-3 space-y-2">
          {flags.map((flag) => (
            <RiskHalo
              key={flag.id}
              level={riskTone(flag.level)}
              label={`${flag.label}: ${riskLabel(flag.level)}`}
            >
              <div className="rounded-md bg-background p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <RiskBadge flag={flag} />
                  <span className="text-xs text-muted-foreground">
                    {riskLabel(flag.level)}
                  </span>
                </div>
                <p className="mt-2 text-sm">{flag.description}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Evidence: {flag.evidence}
                </p>
              </div>
            </RiskHalo>
          ))}
        </div>
      )}
    </section>
  );
}

function PreviewPanel({ data }: { data: BehaviorEditorData }) {
  const preview = data.preview;
  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="behavior-preview"
      aria-labelledby="behavior-preview-heading"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Preview before apply
          </p>
          <h3
            className="mt-1 text-sm font-semibold"
            id="behavior-preview-heading"
          >
            Behavior draft can be tested before it changes production.
          </h3>
        </div>
        <span
          className={cn(
            "inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium",
            RISK_CLASS[preview.risk],
          )}
        >
          {riskLabel(preview.risk)}
        </span>
      </div>

      <dl className="mt-4 space-y-2 text-sm">
        <div>
          <dt className="text-muted-foreground">Affected environments</dt>
          <dd>{preview.affectedEnvironments.join(", ")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Cost</dt>
          <dd>{preview.costDelta}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Rollback</dt>
          <dd>{preview.rollback}</dd>
        </div>
      </dl>

      <ul className="mt-3 space-y-2 text-sm">
        {preview.policyChecks.map((check) => (
          <li key={check} className="rounded-md border bg-background px-3 py-2">
            <ShieldCheck className="mr-2 inline h-4 w-4" aria-hidden />
            {check}
          </li>
        ))}
      </ul>

      {preview.blockedReason ? (
        <p
          className="mt-3 rounded-md border border-warning/50 bg-warning/5 px-3 py-2 text-sm text-muted-foreground"
          data-testid="behavior-preview-blocked"
        >
          {preview.blockedReason}
        </p>
      ) : null}

      <p className="mt-3 text-xs text-muted-foreground">
        Evidence: {preview.evidence}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          data-testid="behavior-run-preview"
        >
          <PlayCircle className="h-4 w-4" aria-hidden />
          Run preview
        </button>
        <button
          type="button"
          disabled={!preview.canApply}
          title={preview.blockedReason ?? undefined}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="behavior-apply-draft"
        >
          <ShieldCheck className="h-4 w-4" aria-hidden />
          Apply draft
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          Revert diff
        </button>
      </div>
    </section>
  );
}

function SemanticDiffPanel({ data }: { data: BehaviorEditorData }) {
  if (data.semanticDiffs.length === 0) {
    return (
      <StatePanel state="empty" title="No semantic diff yet">
        <p>
          Create or import behavior before Studio can explain the semantic
          change.
        </p>
      </StatePanel>
    );
  }
  const primaryDiff = data.semanticDiffs[0]!;
  return (
    <section className="space-y-3" data-testid="behavior-semantic-diff">
      <DiffRibbon
        label="Semantic behavior diff"
        before="Production can answer cancellation questions from the archived refund policy first."
        after="Draft cites the May 2026 refund policy before quoting a refund window."
        impact={primaryDiff.impact}
      />
      <ul className="space-y-2">
        {data.semanticDiffs.map((diff) => (
          <li key={diff.id} className="rounded-md border bg-card p-3 text-sm">
            <p className="font-medium">{diff.summary}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Evidence: {diff.evidence}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Expected effect: {diff.impact}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BehaviorEditor({ data }: BehaviorEditorProps) {
  const [mode, setMode] = useState<BehaviorMode>("plain");
  const sentences = useMemo(() => allSentences(data.sections), [data.sections]);
  const [selectedSentenceId, setSelectedSentenceId] = useState<string | null>(
    sentences[0]?.id ?? null,
  );
  const risks = useMemo(() => riskMap(data.riskFlags), [data.riskFlags]);
  const selectedSentence =
    sentences.find((sentence) => sentence.id === selectedSentenceId) ??
    sentences[0] ??
    null;
  const objectTreatment = OBJECT_STATE_TREATMENTS[data.objectState];
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];
  const isEmpty = data.sections.length === 0;

  return (
    <div className="flex flex-col gap-6" data-testid="behavior-editor">
      <section className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]">
        <div className="rounded-md border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Behavior editor
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
          <dl className="mt-4 grid gap-3 text-sm [grid-template-columns:repeat(auto-fit,minmax(min(100%,10rem),1fr))]">
            <div>
              <dt className="text-muted-foreground">Branch</dt>
              <dd
                className="break-words font-medium"
                data-testid="behavior-branch"
              >
                {data.branch}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Editor state</dt>
              <dd className="font-medium">{objectTreatment.label}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Agent</dt>
              <dd className="break-all font-medium">{data.agentId}</dd>
            </div>
          </dl>
        </div>

        <PreviewPanel data={data} />
      </section>

      <ModeSwitcher mode={mode} onModeChange={setMode} />

      {data.degradedReason ? (
        <StatePanel state="degraded" title="Behavior data is degraded">
          <p>{data.degradedReason}</p>
          <p className="mt-1">
            Cached behavior remains visible. Apply is read-only until the source
            recovers.
          </p>
        </StatePanel>
      ) : null}

      {isEmpty ? (
        <StatePanel state="empty" title="No behavior sections yet">
          <p>
            Import a prompt, create a purpose section, or save a simulator turn
            as the first behavior eval.
          </p>
        </StatePanel>
      ) : null}

      <section className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,20rem),1fr))]">
        <div className="space-y-4">
          {mode === "plain" ? (
            <PlainLanguageMode
              sections={data.sections}
              risks={risks}
              selectedSentenceId={selectedSentence?.id ?? null}
              onSelectSentence={setSelectedSentenceId}
            />
          ) : null}
          {mode === "policy" ? (
            <StructuredPolicyMode sections={data.sections} />
          ) : null}
          {mode === "config" ? (
            <CodeConfigMode sections={data.sections} />
          ) : null}

          <SemanticDiffPanel data={data} />
        </div>

        <aside className="space-y-4">
          <SentenceTelemetryPanel sentence={selectedSentence} />
          <ConfidenceMeter
            value={data.evalCoveragePercent}
            level={data.evalConfidence}
            label="Eval coverage"
            evidence={`Evidence: ${data.evalEvidence}`}
          />
          <RiskPanel flags={data.riskFlags} />
          <EvidenceCallout
            title="Preview evidence"
            source={data.preview.evidence}
            confidence={data.evalCoveragePercent}
            confidenceLevel={data.evalConfidence}
            tone={data.preview.canApply ? "info" : "warning"}
          >
            <p>
              Behavior edits are reversible and previewed against traces, evals,
              policy checks, cost, and rollback before apply.
            </p>
          </EvidenceCallout>
        </aside>
      </section>
    </div>
  );
}
