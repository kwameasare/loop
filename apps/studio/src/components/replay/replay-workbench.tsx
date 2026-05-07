"use client";

import { useMemo, useState } from "react";
import {
  ArrowRight,
  GitFork,
  Pause,
  Play,
  Radar,
  Save,
  TestTube2,
  WandSparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { CostOfContextSlider } from "@/components/trace/cost-of-context-slider";
import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
  StatePanel,
} from "@/components/target";
import {
  type CanonicalScene,
  type FutureReplayDiff,
  type PersonaSimulationResult,
  type ProductionConversationCandidate,
  type ReplayFailureCluster,
  type ReplayWorkbenchModel,
  replayAgainstDraft,
} from "@/lib/replay-workbench";
import { cn } from "@/lib/utils";

const RISK_TONE: Record<ProductionConversationCandidate["risk"], string> = {
  low: "border-success/40 bg-success/10 text-success",
  medium: "border-warning/40 bg-warning/10 text-warning",
  high: "border-destructive/40 bg-destructive/10 text-destructive",
};

const DIFF_TONE: Record<FutureReplayDiff["status"], string> = {
  same: "border-border bg-muted/30 text-muted-foreground",
  changed: "border-info/40 bg-info/10 text-info",
  improved: "border-success/40 bg-success/10 text-success",
  regressed: "border-destructive/40 bg-destructive/10 text-destructive",
};

function ConversationCard({
  conversation,
  active,
  onSelect,
}: {
  conversation: ProductionConversationCandidate;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group rounded-md border bg-card p-4 text-left transition-all duration-standard ease-standard hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm",
        active ? "border-primary/60 ring-2 ring-focus/30" : "border-border",
      )}
      data-testid={`replay-conversation-${conversation.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            {conversation.sourceVersion} to {conversation.draftVersion}
          </p>
          <h3 className="mt-1 text-sm font-semibold">{conversation.title}</h3>
        </div>
        <span
          className={cn("rounded-md border px-2 py-0.5 text-xs", RISK_TONE[conversation.risk])}
        >
          {conversation.risk}
        </span>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{conversation.issue}</p>
      <p className="mt-3 font-mono text-xs text-muted-foreground">
        {conversation.turns} turns - {conversation.traceId} - {conversation.snapshotId}
      </p>
    </button>
  );
}

function FutureReplayPanel({
  model,
  selected,
}: {
  model: ReplayWorkbenchModel;
  selected: ProductionConversationCandidate;
}) {
  const [playing, setPlaying] = useState(false);
  const [forked, setForked] = useState(false);
  const [savedEval, setSavedEval] = useState(false);
  const [runningFutureReplay, setRunningFutureReplay] = useState(false);
  const [liveReplay, setLiveReplay] = useState(model.selectedReplay);
  const replay = liveReplay;
  async function handleReplayAgainstDraft() {
    setRunningFutureReplay(true);
    try {
      const result = await replayAgainstDraft(selected.agentId, {
        traceIds: [selected.traceId],
        draftBranchRef: selected.draftVersion,
        compareVersionRef: selected.sourceVersion,
      });
      setLiveReplay(result.items[0] ?? model.selectedReplay);
    } finally {
      setRunningFutureReplay(false);
    }
  }
  return (
    <section className="space-y-4" data-testid="production-replay">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Production Replay Against The Future
          </p>
          <h2 className="mt-1 text-lg font-semibold">{selected.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Real production inputs are replayed against the draft before the
            draft can surprise production.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleReplayAgainstDraft}
            disabled={runningFutureReplay}
          >
            <WandSparkles className="mr-2 h-4 w-4" />
            {runningFutureReplay ? "Replaying..." : "Replay against my draft"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setPlaying((current) => !current)}
          >
            {playing ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
            {playing ? "Pause timeline" : "Play timeline"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setForked(true)}
          >
            <GitFork className="mr-2 h-4 w-4" />
            Fork from frame
          </Button>
          <Button type="button" size="sm" onClick={() => setSavedEval(true)}>
            <TestTube2 className="mr-2 h-4 w-4" />
            Save as eval
          </Button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricTile
          label="Behavioral distance"
          value={`${replay.behavioralDistance}%`}
          tone="watching"
          detail={`${replay.changedFrames} changed frames`}
        />
        <MetricTile
          label="Latency delta"
          value={`${replay.latencyDeltaMs} ms`}
          tone="healthy"
          detail="Draft is faster"
        />
        <MetricTile
          label="Cost delta"
          value={`${replay.costDeltaPct}%`}
          tone="healthy"
          detail="Same traffic mix"
        />
        <MetricTile
          label="Top break"
          value="1 P1"
          tone="blocked"
          detail="Legal handoff synonym"
        />
      </div>

      <EvidenceCallout
        title="What could break"
        tone="warning"
        confidence={84}
        source={`${selected.traceId}/future-replay`}
      >
        {replay.mostLikelyBreak}
      </EvidenceCallout>

      {(forked || savedEval) ? (
        <StatePanel state="success" title="Replay evidence promoted">
          {forked ? "A branch can now start from the selected frame. " : ""}
          {savedEval ? "This conversation is queued as a regression eval. " : ""}
          The action is local to the draft until promotion gates pass.
        </StatePanel>
      ) : null}

      <div className="overflow-hidden rounded-md border bg-card" data-testid="future-replay-diff">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/30 px-3 py-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Token-aligned replay diff
          </p>
          <p className="text-xs text-muted-foreground">
            Production and draft stay stacked until there is enough room to compare side by side.
          </p>
        </div>
        {replay.diffRows.map((row) => (
          <article
            key={row.id}
            className="border-b px-3 py-3 text-sm last:border-b-0"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium">{row.frame}</p>
                <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                  {row.evidenceRef}
                </p>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-md border px-2 py-1 text-xs font-medium",
                  DIFF_TONE[row.status],
                )}
              >
                {row.status}
              </span>
            </div>
            <div className="mt-3 grid gap-3 2xl:grid-cols-2">
              <DiffText label="Production" text={row.baseline} muted={true} />
              <DiffText label="Draft" text={row.draft} muted={false} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function DiffText({
  label,
  text,
  muted,
}: {
  label: string;
  text: string;
  muted: boolean;
}) {
  return (
    <div className="min-w-0 rounded-md bg-muted/35 p-3">
      <p className="text-[11px] font-semibold uppercase text-muted-foreground">{label}</p>
      <p className={cn("mt-1 break-words", muted && "text-muted-foreground")}>{text}</p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "healthy" | "watching" | "blocked";
}) {
  const toneClass =
    tone === "healthy"
      ? "border-success/40 bg-success/5"
      : tone === "blocked"
        ? "border-destructive/40 bg-destructive/5"
        : "border-info/40 bg-info/5";
  return (
    <article className={cn("rounded-md border p-4", toneClass)}>
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </article>
  );
}

function PersonaSimulator({
  personas,
}: {
  personas: readonly PersonaSimulationResult[];
}) {
  const [converted, setConverted] = useState<string[]>([]);
  return (
    <section className="space-y-3" data-testid="persona-simulator">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            First User Persona Simulator
          </p>
          <h2 className="mt-1 text-lg font-semibold">Who fails, not just what fails</h2>
        </div>
        <LiveBadge tone="staged">50 scenarios</LiveBadge>
      </div>
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
        {personas.map((persona) => {
          const isConverted = converted.includes(persona.id);
          return (
            <article key={persona.id} className="rounded-md border bg-card p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="min-w-0 flex-1 text-sm font-semibold">{persona.persona}</h3>
                <span className="shrink-0 text-xs font-semibold tabular-nums">
                  {persona.passRate}%
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{persona.lens}</p>
              <ConfidenceMeter
                className="mt-3"
                value={persona.passRate}
                label="Persona pass rate"
                evidence={`${persona.failedScenarios} failed of ${persona.scenarios}`}
              />
              <p className="mt-3 text-xs text-muted-foreground">{persona.insight}</p>
              <Button
                type="button"
                variant={isConverted ? "subtle" : "outline"}
                size="sm"
                className="mt-3 min-h-9 w-full whitespace-normal"
                onClick={() =>
                  setConverted((current) =>
                    current.includes(persona.id)
                      ? current
                      : [...current, persona.id],
                  )
                }
              >
                <Save className="mr-2 h-4 w-4" />
                {isConverted ? "Eval linked" : "Convert to eval"}
              </Button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function PropertyTester({ model }: { model: ReplayWorkbenchModel }) {
  return (
    <section className="space-y-3" data-testid="conversation-property-tester">
      <div>
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          Conversation Property Tester
        </p>
        <h2 className="mt-1 text-lg font-semibold">Simulate 100 like this</h2>
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_0.8fr]">
        <div className="space-y-3">
          {model.properties.map((result) => (
            <article key={result.id} className="rounded-md border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-semibold">{result.axis}</h3>
                <LiveBadge tone={result.robustness >= 90 ? "live" : "canary"}>
                  {result.samples} samples
                </LiveBadge>
              </div>
              <ConfidenceMeter
                className="mt-3"
                value={result.robustness}
                label="Robustness"
                evidence={`${result.failures} failures clustered from one conversation`}
              />
              <p className="mt-3 rounded-md bg-muted/40 p-3 font-mono text-xs">
                {result.representativeFailure}
              </p>
              <p className="mt-3 text-sm text-muted-foreground">{result.nextAction}</p>
            </article>
          ))}
        </div>
        <div className="rounded-md border bg-card p-4">
          <h3 className="text-sm font-semibold">Failure clusters</h3>
          <div className="mt-3 space-y-3">
            {model.clusters.map((cluster) => (
              <ClusterRow key={cluster.id} cluster={cluster} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function ClusterRow({ cluster }: { cluster: ReplayFailureCluster }) {
  return (
    <article className="rounded-md border bg-background p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-medium">{cluster.label}</h4>
          <p className="mt-1 text-xs text-muted-foreground">{cluster.evidenceRef}</p>
        </div>
        <span className={cn("rounded-md border px-2 py-0.5 text-xs", RISK_TONE[cluster.severity])}>
          {cluster.count}
        </span>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{cluster.nextAction}</p>
    </article>
  );
}

function SceneLibrary({ scenes }: { scenes: readonly CanonicalScene[] }) {
  const [saved, setSaved] = useState<string[]>([]);
  return (
    <section className="space-y-3" data-testid="scene-library">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Scenes
          </p>
          <h2 className="mt-1 text-lg font-semibold">Canonical production conversations</h2>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setSaved((current) => [...new Set([...current, scenes[0]?.id ?? "scene"])])}
        >
          <WandSparkles className="mr-2 h-4 w-4" />
          Canonicalize selected
        </Button>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {scenes.map((scene) => (
          <article key={scene.id} className="rounded-md border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{scene.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {scene.source} - {scene.turns} turns - {scene.linkedTraceId}
                </p>
              </div>
              <LiveBadge tone={scene.evalLinked || saved.includes(scene.id) ? "live" : "draft"}>
                {scene.evalLinked || saved.includes(scene.id) ? "Eval linked" : "Draft"}
              </LiveBadge>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{scene.summary}</p>
            <p className="mt-3 rounded-md bg-muted/40 p-2 text-xs text-muted-foreground">
              {scene.provenance}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ReplayWorkbench({ model }: { model: ReplayWorkbenchModel }) {
  const [selectedId, setSelectedId] = useState(model.conversations[0]?.id ?? "");
  const selected = useMemo(
    () =>
      model.conversations.find((conversation) => conversation.id === selectedId) ??
      model.conversations[0],
    [model.conversations, selectedId],
  );

  if (!selected) {
    return (
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
        <StatePanel state="empty" title="No production conversations">
          Connect production traces before replay can generate future tests.
        </StatePanel>
      </main>
    );
  }

  return (
    <main
      className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-6"
      data-testid="replay-workbench"
    >
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Test / Replay Workbench
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            Replay production against tomorrow
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Every production turn can become a replay, persona simulation,
            property test, eval seed, and canonical scene with evidence intact.
          </p>
        </div>
        <Button type="button">
          Run top 100 risky turns
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </header>

      <section className="grid gap-6 xl:grid-cols-[0.72fr_1.28fr]">
        <div className="space-y-3" data-testid="production-conversation-candidates">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Production candidates</h2>
            <LiveBadge tone="canary">ranked by break risk</LiveBadge>
          </div>
          {model.conversations.map((conversation) => (
            <ConversationCard
              key={conversation.id}
              conversation={conversation}
              active={conversation.id === selected.id}
              onSelect={() => setSelectedId(conversation.id)}
            />
          ))}
        </div>
        <FutureReplayPanel model={model} selected={selected} />
      </section>

      <PersonaSimulator personas={model.personas} />
      <PropertyTester model={model} />
      <CostOfContextSlider
        agentId={selected.agentId}
        turnId={selected.traceId}
      />
      <SceneLibrary scenes={model.scenes} />

      <section className="rounded-md border bg-card p-4" data-testid="comments-as-spec">
        <div className="flex items-start gap-3">
          <Radar className="mt-0.5 h-5 w-5 text-info" aria-hidden={true} />
          <div>
            <h2 className="text-sm font-semibold">Comments become specifications</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Resolving a review comment with expected behavior spawns an eval
              case, links it to the source trace, and keeps the scene in the
              library after cutover.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
