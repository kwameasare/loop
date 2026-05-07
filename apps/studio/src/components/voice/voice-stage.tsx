"use client";

import { useMemo, useState } from "react";
import {
  Link2,
  Mic,
  Pause,
  PhoneCall,
  Radio,
  RotateCcw,
  Volume2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfidenceMeter, EvidenceCallout, LiveBadge } from "@/components/target";
import {
  provisionVoiceNumber,
  type VoiceLatencySpan,
  type VoiceStageModel,
} from "@/lib/voice-stage";
import { cn } from "@/lib/utils";

const SPAN_TONE: Record<VoiceLatencySpan["status"], string> = {
  ok: "border-success/40 bg-success/10 text-success",
  watch: "border-warning/40 bg-warning/10 text-warning",
  over: "border-destructive/40 bg-destructive/10 text-destructive",
};

const SPEAKER_TONE: Record<VoiceStageModel["transcript"][number]["speaker"], string> = {
  caller: "border-info/40 bg-info/10 text-info",
  agent: "border-success/40 bg-success/10 text-success",
  tool: "border-warning/40 bg-warning/10 text-warning",
};

function Waveform({ levels, paused }: { levels: readonly number[]; paused: boolean }) {
  return (
    <div
      className="flex h-28 items-center gap-1 rounded-md border bg-card px-4"
      aria-label="Live voice waveform"
      role="img"
    >
      {levels.map((level, index) => (
        <span
          key={`${level}-${index}`}
          className={cn(
            "w-full rounded-full bg-info transition-all duration-gentle",
            paused ? "opacity-40" : "animate-pulse",
          )}
          style={{
            height: `${Math.max(10, level)}%`,
            animationDelay: `${index * 60}ms`,
          }}
        />
      ))}
    </div>
  );
}

function LatencyBudget({ spans }: { spans: readonly VoiceLatencySpan[] }) {
  const total = spans.reduce((sum, span) => sum + span.ms, 0);
  const budget = spans.reduce((sum, span) => sum + span.budgetMs, 0);
  return (
    <section className="rounded-md border bg-card p-4" data-testid="voice-latency-budget">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Latency budget</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            ASR, model, tool, and TTS spans stay visible together.
          </p>
        </div>
        <LiveBadge tone={total <= budget ? "live" : "canary"}>
          {total} ms / {budget} ms
        </LiveBadge>
      </div>
      <div className="mt-4 flex h-4 overflow-hidden rounded-full bg-muted">
        {spans.map((span) => (
          <div
            key={span.id}
            className={cn(
              "border-r border-background last:border-r-0",
              span.status === "ok"
                ? "bg-success"
                : span.status === "watch"
                  ? "bg-warning"
                  : "bg-destructive",
            )}
            style={{ width: `${Math.max(8, (span.ms / total) * 100)}%` }}
            title={`${span.label}: ${span.ms} ms`}
          />
        ))}
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {spans.map((span) => (
          <article key={span.id} className="rounded-md border bg-background p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">{span.label}</p>
              <span className={cn("rounded-md border px-2 py-0.5 text-xs", SPAN_TONE[span.status])}>
                {span.status}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {span.ms} ms observed - {span.budgetMs} ms budget
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function VoiceStage({
  model,
  workspaceId,
}: {
  model: VoiceStageModel;
  workspaceId?: string;
}) {
  const [paused, setPaused] = useState(false);
  const [demoId, setDemoId] = useState<string | null>(null);
  const [bargeInArmed, setBargeInArmed] = useState(model.config.bargeIn);
  const [provisioned, setProvisioned] = useState<string | null>(null);
  const score = useMemo(
    () =>
      Math.round(
        model.evals.reduce((sum, evalCase) => sum + evalCase.passRate, 0) /
          Math.max(1, model.evals.length),
      ),
    [model.evals],
  );

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-6" data-testid="voice-stage">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Observe / Voice Stage
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            {model.agentName}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Voice is a first-class channel: waveform, ASR, TTS, barge-in,
            latency, evals, queued speech, and expiring demo links are all
            visible before production.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setPaused((current) => !current)}
          >
            {paused ? <Radio className="mr-2 h-4 w-4" /> : <Pause className="mr-2 h-4 w-4" />}
            {paused ? "Resume stream" : "Pause stream"}
          </Button>
          <Button type="button">
            <PhoneCall className="mr-2 h-4 w-4" />
            Start staging call
          </Button>
          {workspaceId ? (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                void provisionVoiceNumber(workspaceId).then((number) =>
                  setProvisioned(number.phone_number),
                )
              }
              data-testid="voice-provision-number"
            >
              Get a phone number
            </Button>
          ) : null}
        </div>
      </header>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          <Waveform levels={model.waveform} paused={paused} />
          <div className="rounded-md border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold">Live transcript</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Queued speech appears in staging before TTS speaks it.
                </p>
              </div>
              <LiveBadge tone="staged">{model.callState}</LiveBadge>
            </div>
            <div className="mt-4 space-y-3">
              {model.transcript.map((turn) => (
                <article key={turn.id} className="rounded-md border bg-background p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className={cn("rounded-md border px-2 py-0.5 text-xs", SPEAKER_TONE[turn.speaker])}>
                      {turn.speaker}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {turn.timestamp}
                    </span>
                  </div>
                  <p className="mt-2 text-sm">{turn.text}</p>
                </article>
              ))}
            </div>
            <EvidenceCallout
              className="mt-4"
              title="Queued speech preview"
              tone="info"
              source="voice-stage/staging/queued-speech"
              confidence={92}
            >
              {model.queuedSpeech}
            </EvidenceCallout>
          </div>
        </div>

        <div className="space-y-4">
          <section className="rounded-md border bg-card p-4" data-testid="voice-config-summary">
            <div className="flex items-center gap-3">
              <Mic className="h-5 w-5 text-info" aria-hidden={true} />
              <div>
                <h2 className="text-sm font-semibold">Voice config</h2>
                <p className="text-xs text-muted-foreground">{model.config.phoneNumber}</p>
              </div>
            </div>
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">ASR</dt>
                <dd>{model.config.asr}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">TTS</dt>
                <dd>{model.config.tts}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Voice</dt>
                <dd>{model.config.voice}</dd>
              </div>
            </dl>
            {provisioned ? (
              <EvidenceCallout
                className="mt-4"
                title="Phone number provisioned"
                tone="success"
                source="voice/numbers/provision"
              >
                {provisioned} is routed through the LiveKit SIP trunk. Complete
                any pending compliance checklist before production traffic.
              </EvidenceCallout>
            ) : null}
            <button
              type="button"
              className={cn(
                "mt-4 flex w-full items-center justify-between rounded-md border px-3 py-2 text-sm transition-colors hover:bg-muted",
                bargeInArmed ? "border-success/40 bg-success/5" : "border-warning/40 bg-warning/5",
              )}
              onClick={() => setBargeInArmed((current) => !current)}
              aria-pressed={bargeInArmed}
            >
              <span>Barge-in</span>
              <span>{bargeInArmed ? "Armed" : "Muted"}</span>
            </button>
          </section>

          <LatencyBudget spans={model.spans} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]" data-testid="voice-evals-and-links">
        <div className="rounded-md border bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Voice evals</h2>
            <LiveBadge tone="live">{score}% avg</LiveBadge>
          </div>
          <div className="mt-4 space-y-3">
            {model.evals.map((evalCase) => (
              <article key={evalCase.id} className="rounded-md border bg-background p-3">
                <h3 className="text-sm font-medium">{evalCase.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {evalCase.coverage}
                </p>
                <ConfidenceMeter
                  className="mt-3"
                  value={evalCase.passRate}
                  label="Pass rate"
                  evidence={evalCase.evidenceRef}
                />
              </article>
            ))}
          </div>
        </div>

        <div className="rounded-md border bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Audited demo links</h2>
            <Volume2 className="h-5 w-5 text-info" aria-hidden={true} />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {model.demoLinks.map((link) => {
              const active = demoId === link.id;
              return (
                <article key={link.id} className="rounded-md border bg-background p-3">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-sm font-medium">{link.label}</h3>
                    <LiveBadge tone={link.audited ? "live" : "paused"}>
                      {link.expiresIn}
                    </LiveBadge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{link.scope}</p>
                  <Button
                    type="button"
                    variant={active ? "subtle" : "outline"}
                    size="sm"
                    className="mt-3 w-full"
                    onClick={() => setDemoId(link.id)}
                  >
                    <Link2 className="mr-2 h-4 w-4" />
                    {active ? "Link copied to audit log" : "Generate link"}
                  </Button>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <EvidenceCallout
        title="Honest first message"
        tone="neutral"
        source="voice-stage/staging/headers"
      >
        Every voice turn carries a trace id, version, and snapshot id so an
        operator can replay exactly what happened later.
      </EvidenceCallout>

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline">
          <RotateCcw className="mr-2 h-4 w-4" />
          Replay with memory cleared
        </Button>
        <Button type="button" variant="outline">
          <Mic className="mr-2 h-4 w-4" />
          Run interruption suite
        </Button>
      </div>
    </main>
  );
}
