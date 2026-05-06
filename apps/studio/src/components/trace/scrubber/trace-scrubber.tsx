"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BookmarkPlus,
  GitFork,
  Pause,
  Play,
  StepBack,
  StepForward,
} from "lucide-react";

import { EvidenceCallout, LiveBadge, StatePanel } from "@/components/target";
import {
  buildTraceScrubberModel,
  type TraceScrubberFrame,
} from "@/lib/trace-scrubber";
import { formatDurationNs, formatUsd, type Trace } from "@/lib/traces";
import { cn } from "@/lib/utils";

const SPEEDS = [1, 2, 4] as const;

function statusTone(status: TraceScrubberFrame["status"]) {
  if (status === "error") return "text-destructive";
  if (status === "unset") return "text-muted-foreground";
  return "text-success";
}

export function TraceScrubber({ trace }: { trace: Trace }) {
  const model = useMemo(() => buildTraceScrubberModel(trace), [trace]);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [action, setAction] = useState<string | null>(null);
  const frame = model.frames[frameIndex] ?? model.frames[0] ?? null;

  useEffect(() => {
    setFrameIndex(0);
    setPlaying(false);
    setAction(null);
  }, [trace.id]);

  useEffect(() => {
    if (!playing || model.frames.length <= 1) return;
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setPlaying(false);
      return;
    }
    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= model.frames.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 900 / speed);
    return () => window.clearInterval(timer);
  }, [model.frames.length, playing, speed]);

  if (!frame) {
    return (
      <StatePanel state="empty" title="Trace scrubber unavailable">
        {model.unsupportedReason ??
          "Trace frames are not available for this trace."}
      </StatePanel>
    );
  }

  function selectFrame(next: number) {
    setFrameIndex(Math.max(0, Math.min(model.frames.length - 1, next)));
  }

  function forkFrame() {
    if (!frame) return;
    setAction(`${frame.forkLabel} queued against ${model.identity.version}.`);
  }

  function saveFrame() {
    if (!frame) return;
    setAction(
      `${frame.saveLabel} queued with trace ${model.identity.traceId}.`,
    );
  }

  function handleKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === " ") {
      event.preventDefault();
      setPlaying((value) => !value);
    }
    if (event.key.toLowerCase() === "f") {
      event.preventDefault();
      forkFrame();
    }
    if (event.key.toLowerCase() === "s") {
      event.preventDefault();
      saveFrame();
    }
  }

  return (
    <section
      aria-labelledby="trace-scrubber-heading"
      className="space-y-4 rounded-md border bg-card p-4"
      data-testid="trace-scrubber"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Trace scrubber
          </p>
          <h2
            className="mt-1 text-lg font-semibold"
            id="trace-scrubber-heading"
          >
            Frame-by-frame decision footage
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Drag or step the playhead. Every frame is derived from recorded span
            state.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <LiveBadge tone="staged">{model.identity.version}</LiveBadge>
          <LiveBadge tone="draft">{model.identity.snapshotId}</LiveBadge>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)]">
        <div className="min-w-0 space-y-3">
          <div className="rounded-md border bg-muted/30 p-3">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">{frame.label}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDurationNs(frame.latencyNs)} elapsed of{" "}
                  {formatDurationNs(model.totalNs)}
                </p>
              </div>
              <p
                className={cn(
                  "text-xs font-semibold",
                  statusTone(frame.status),
                )}
              >
                {frame.status} - {frame.category}
              </p>
            </div>
            <input
              aria-label="Trace scrubber playhead"
              className="w-full accent-primary"
              data-testid="trace-scrubber-range"
              max={model.frames.length - 1}
              min={0}
              onChange={(event) => selectFrame(Number(event.target.value))}
              onKeyDown={handleKey}
              type="range"
              value={frameIndex}
            />
            <ol
              className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(3rem,1fr))] gap-1"
              aria-label="Trace frames"
            >
              {model.frames.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-current={
                      item.index === frameIndex ? "step" : undefined
                    }
                    className={cn(
                      "h-8 w-full rounded-md border px-1 text-[0.68rem] font-medium focus-visible:ring-2 focus-visible:ring-ring",
                      item.index === frameIndex
                        ? "border-primary bg-primary text-primary-foreground"
                        : "bg-background text-muted-foreground hover:bg-muted",
                    )}
                    onClick={() => selectFrame(item.index)}
                  >
                    {item.index + 1}
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              onClick={() => selectFrame(frameIndex - 1)}
              data-testid="trace-scrubber-prev"
            >
              <StepBack className="h-4 w-4" aria-hidden />
              Step
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
              onClick={() => setPlaying((value) => !value)}
              data-testid="trace-scrubber-play"
            >
              {playing ? (
                <Pause className="h-4 w-4" aria-hidden />
              ) : (
                <Play className="h-4 w-4" aria-hidden />
              )}
              {playing ? "Pause" : "Play"}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              onClick={() => selectFrame(frameIndex + 1)}
              data-testid="trace-scrubber-next"
            >
              <StepForward className="h-4 w-4" aria-hidden />
              Step
            </button>
            <div
              className="flex rounded-md border p-1"
              role="group"
              aria-label="Playback speed"
            >
              {SPEEDS.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={speed === item}
                  className={cn(
                    "rounded px-2 py-1 text-xs",
                    speed === item
                      ? "bg-muted font-semibold"
                      : "text-muted-foreground hover:bg-muted/70",
                  )}
                  onClick={() => setSpeed(item)}
                >
                  {item}x
                </button>
              ))}
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              onClick={forkFrame}
              data-testid="trace-scrubber-fork"
            >
              <GitFork className="h-4 w-4" aria-hidden />
              Fork
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              onClick={saveFrame}
              data-testid="trace-scrubber-save"
            >
              <BookmarkPlus className="h-4 w-4" aria-hidden />
              Save
            </button>
          </div>

          {action ? (
            <StatePanel state="success" title="Local replay action queued">
              <span data-testid="trace-scrubber-action">{action}</span>
            </StatePanel>
          ) : null}
        </div>

        <aside className="min-w-0 space-y-3" data-testid="trace-frame-detail">
          <EvidenceCallout
            title="Frame evidence"
            source={frame.evidence}
            confidence={frame.status === "error" ? 58 : 84}
            confidenceLevel={frame.status === "error" ? "low" : "medium"}
            tone={frame.status === "error" ? "warning" : "info"}
          >
            {frame.spanName} at {formatDurationNs(frame.atNs)}.
          </EvidenceCallout>
          <dl className="grid gap-2 text-sm">
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Active model context
              </dt>
              <dd>{frame.activeModelContext}</dd>
            </div>
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Next tool under consideration
              </dt>
              <dd>{frame.nextToolCall}</dd>
            </div>
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Retrieval candidates
              </dt>
              <dd>{frame.retrievalState}</dd>
            </div>
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Memory before commit
              </dt>
              <dd>{frame.memoryState}</dd>
            </div>
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Policy or budget gate
              </dt>
              <dd>{frame.gateState}</dd>
            </div>
            <div className="rounded-md border bg-background p-2">
              <dt className="text-xs font-semibold text-muted-foreground">
                Streaming response
              </dt>
              <dd>{frame.streamingState}</dd>
            </div>
          </dl>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md border bg-background p-2">
              <p className="text-xs font-semibold text-muted-foreground">
                Cost
              </p>
              <p>{formatUsd(frame.costUsd)}</p>
            </div>
            <div className="rounded-md border bg-background p-2">
              <p className="text-xs font-semibold text-muted-foreground">
                Latency
              </p>
              <p>{formatDurationNs(frame.latencyNs)}</p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
