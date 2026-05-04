"use client";

/**
 * P0.3: Agent inspector — runtime trace replay.
 *
 * Replaces the previous 3-hardcoded-step demo with a real fetch
 * against ``GET /v1/traces/{turn_id}``. Each span becomes a flow
 * frame; the variable state is sourced from span attributes when
 * present (the cp-side runtime currently emits sparse attributes
 * — the inspector renders empty state cleanly until the runtime
 * produces richer payloads).
 *
 * Without a turn_id query param the page renders an empty state
 * inviting the operator to pick a trace from /traces. When the user
 * does, this page receives ``?turn=<turn_id>`` and replays it.
 */

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { VariableInspector } from "@/components/flow/variable-inspector";
import {
  captureFrame,
  type FlowFrame,
  type FlowVariableValue,
} from "@/lib/flow-inspector";
import { fetchTraceByTurnId, type Trace } from "@/lib/traces";

function spansToFrames(trace: Trace): FlowFrame[] {
  // Children-after-parent depth-first ordering; the studio's flow
  // inspector renders frames in order so this gives a sensible
  // play-by-play of the turn.
  const ordered = [...trace.spans].sort((a, b) => a.start_ns - b.start_ns);
  return ordered.map((span, i) => {
    const state: Record<string, FlowVariableValue> = {};
    for (const [k, v] of Object.entries(span.attributes ?? {})) {
      // FlowVariableValue is a strict union; coerce numbers/booleans/strings
      // through and stringify anything else.
      if (
        typeof v === "string" ||
        typeof v === "number" ||
        typeof v === "boolean"
      ) {
        state[k] = v;
      } else {
        state[k] = JSON.stringify(v);
      }
    }
    state["_status"] = span.status;
    return captureFrame(
      span.id || `span-${i}`,
      span.name || `span ${i + 1}`,
      state,
    );
  });
}

export default function InspectorPage() {
  return (
    <RequireAuth>
      <InspectorBody />
    </RequireAuth>
  );
}

function InspectorBody() {
  const params = useSearchParams();
  const turnId = params.get("turn");
  const [frames, setFrames] = useState<FlowFrame[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!turnId) {
      setLoaded(true);
      return;
    }
    let cancelled = false;
    void fetchTraceByTurnId(turnId)
      .then((trace) => {
        if (cancelled) return;
        if (trace) {
          setFrames(spansToFrames(trace));
        }
        setLoaded(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load trace");
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [turnId]);

  return (
    <main className="flex min-h-screen">
      <section className="flex flex-1 flex-col gap-4 p-8">
        <header>
          <h1 className="text-xl font-semibold">Inspector</h1>
        </header>
        {!turnId ? (
          <p
            className="text-sm text-zinc-600"
            data-testid="inspector-no-trace"
          >
            Pick a trace from the <a className="underline" href="/traces">Traces</a> tab to
            replay it here. The inspector mirrors each span as a frame so you
            can step through the turn and watch state evolve.
          </p>
        ) : error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : !loaded ? (
          <p
            className="text-sm text-zinc-600"
            data-testid="inspector-loading"
          >
            Loading trace…
          </p>
        ) : frames.length === 0 ? (
          <p
            className="text-sm text-zinc-600"
            data-testid="inspector-empty"
          >
            Trace not found, or the runtime hasn&apos;t emitted spans for this
            turn yet.
          </p>
        ) : (
          <p className="text-sm text-zinc-600">
            Replaying {frames.length} span{frames.length === 1 ? "" : "s"} from
            turn <span className="font-mono">{turnId}</span>.
          </p>
        )}
      </section>
      <VariableInspector frames={frames} running={false} />
    </main>
  );
}
