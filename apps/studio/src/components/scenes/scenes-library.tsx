"use client";

import Link from "next/link";
import { BookOpenCheck, Play, Route } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { LiveBadge } from "@/components/target";
import {
  replayWorkspaceScene,
  type SceneReplayResult,
  type WorkspaceScene,
} from "@/lib/scenes";

export function ScenesLibrary({
  workspaceId,
  scenes,
}: {
  workspaceId: string;
  scenes: readonly WorkspaceScene[];
}): JSX.Element {
  const [replayResults, setReplayResults] = useState<
    Record<string, SceneReplayResult>
  >({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function replay(scene: WorkspaceScene): Promise<void> {
    setBusy(scene.id);
    setError(null);
    try {
      const result = await replayWorkspaceScene(workspaceId, scene.id);
      setReplayResults((current) => ({ ...current, [scene.id]: result }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not replay this scene.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-6">
      <header className="instrument-panel rounded-2xl p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Test / Scenes
        </p>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Production conversation scenes
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Canonical conversations saved from traces, migrations, reviews,
              and incidents. Use them to teach new builders and replay behavior
              without relying on tribal memory.
            </p>
          </div>
          <Link
            href="/replay"
            className="interactive-lift inline-flex h-9 items-center justify-center rounded-md border bg-background px-3 text-sm font-medium transition-colors hover:bg-muted"
          >
            <Route className="mr-2 h-4 w-4" aria-hidden />
            Canonicalize from replay
          </Link>
        </div>
      </header>

      {error ? (
        <section
          className="rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
          role="alert"
        >
          {error}
        </section>
      ) : null}

      {scenes.length === 0 ? (
        <section
          className="instrument-panel rounded-2xl p-6"
          data-testid="scenes-empty"
        >
          <BookOpenCheck
            className="h-6 w-6 text-muted-foreground"
            aria-hidden
          />
          <h2 className="mt-3 text-base font-semibold">
            No scenes canonicalized yet
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Save a production replay, migration parity case, or reviewed
            incident as a scene so future changes can be rehearsed against real
            workspace behavior.
          </p>
          <Link
            href="/replay"
            className="mt-4 inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Open Replay Workbench
          </Link>
        </section>
      ) : (
        <section
          className="grid gap-3 md:grid-cols-2 xl:grid-cols-3"
          data-testid="scenes-grid"
        >
          {scenes.map((scene) => {
            const result = replayResults[scene.id];
            return (
              <article key={scene.id} className="instrument-panel rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-semibold">
                      {scene.name}
                    </h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {scene.category} · {scene.trace_ids.length} trace(s)
                    </p>
                  </div>
                  <LiveBadge tone={result ? "live" : "draft"}>
                    {result ? result.status : "Scene"}
                  </LiveBadge>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {scene.expected_behavior || "Expected behavior not recorded."}
                </p>
                <p className="mt-3 rounded-md bg-muted/40 p-2 font-mono text-xs text-muted-foreground">
                  traces:{" "}
                  {scene.trace_ids.length ? scene.trace_ids.join(", ") : "none"}
                </p>
                {result ? (
                  <p
                    className="mt-3 rounded-md border border-success/40 bg-success/10 p-2 text-xs text-success"
                    data-testid={`scene-replay-${scene.id}`}
                  >
                    Replay {result.draft_replay_id} queued for{" "}
                    {result.trace_ids.length} trace(s).
                  </p>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={() => void replay(scene)}
                  disabled={busy === scene.id}
                  data-testid={`scene-replay-button-${scene.id}`}
                >
                  <Play className="mr-2 h-4 w-4" aria-hidden />
                  {busy === scene.id ? "Queueing" : "Replay scene"}
                </Button>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
