"use client";

import { useState } from "react";

import {
  AmbientHeartbeat,
  CharacterSkeleton,
  CompletionMark,
  EarnedMoment,
} from "@/components/polish";
import { AMBIENT_LIFE_SOURCES, EARNED_MOMENT_IDS } from "@/lib/polish";

export default function PolishDemoPage(): JSX.Element {
  const [reducePolish, setReducePolish] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const fired = new Set<string>();

  return (
    <main
      className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6"
      aria-label="Creative polish primitives"
    >
      <header>
        <h1 className="text-xl font-semibold">Creative polish primitives</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Earned moments, ambient life, character skeletons, and completion
          marks. All signals are tied to real state and never use forbidden
          motion (§29.3).
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox"
              data-testid="toggle-reduce-polish"
              checked={reducePolish}
              onChange={(event) => setReducePolish(event.target.checked)}
            />
            Reduce polish
          </label>
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox"
              data-testid="toggle-reduced-motion"
              checked={reducedMotion}
              onChange={(event) => setReducedMotion(event.target.checked)}
            />
            Reduced motion
          </label>
        </div>
      </header>

      <section aria-label="Earned moments" className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Earned moments
        </h2>
        <div className="flex flex-wrap gap-2">
          {EARNED_MOMENT_IDS.slice(0, 4).map((id) => (
            <EarnedMoment
              key={id}
              momentId={id}
              userId="u_demo"
              objectId="agent_demo"
              fired={fired}
              preferences={{ reducePolish, reducedMotion }}
            />
          ))}
        </div>
      </section>

      <section aria-label="Ambient life" className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Ambient life
        </h2>
        <div className="flex flex-wrap gap-3">
          {AMBIENT_LIFE_SOURCES.map((source) => (
            <AmbientHeartbeat
              key={source}
              source={source}
              lastBeatAt={Date.now()}
              forceStatic={reducedMotion}
            />
          ))}
        </div>
      </section>

      <section aria-label="Skeletons" className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <CharacterSkeleton shape="trace" rows={4} />
        <CharacterSkeleton shape="conversation" rows={5} />
        <CharacterSkeleton shape="eval" rows={6} />
        <CharacterSkeleton shape="chart" rows={8} />
      </section>

      <section aria-label="Completion marks" className="flex flex-wrap gap-2">
        <CompletionMark label="Deploy promoted" proofHref="#deploy-proof" />
        <CompletionMark label="Eval suite clean" proofHref="#eval-proof" />
      </section>
    </main>
  );
}
