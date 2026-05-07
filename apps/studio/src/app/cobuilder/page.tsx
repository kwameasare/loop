"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { CoBuilderPanel } from "@/components/ai-cobuilder/co-builder-panel";
import { RubberDuck } from "@/components/ai-cobuilder/rubber-duck";
import { SecondPairOfEyes } from "@/components/ai-cobuilder/second-pair-of-eyes";
import {
  fetchCoBuilderWorkspace,
  type CoBuilderWorkspace,
} from "@/lib/ai-cobuilder";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function CoBuilderPage(): JSX.Element {
  return (
    <RequireAuth>
      <CoBuilderPageBody />
    </RequireAuth>
  );
}

function CoBuilderPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [workspace, setWorkspace] = useState<CoBuilderWorkspace | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setWorkspace(null);
    setError(null);
    void fetchCoBuilderWorkspace(active.id)
      .then((next) => {
        if (cancelled) return;
        setWorkspace(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load Co-Builder",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active || (!workspace && !error)) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">Loading Co-Builder...</p>
      </main>
    );
  }

  return (
    <main
      data-testid="cobuilder-page"
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          AI Co-Builder
        </p>
        <h1 className="text-2xl font-semibold">Suggest, Edit, Drive</h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Every action declares its mode, exact diff, provenance, and budget.
          Apply is gated until consent passes. Rubber Duck explains failing
          traces; Second Pair of Eyes runs adversarial review.
        </p>
      </header>

      {error ? (
        <p
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      {workspace ? (
        <section className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
          Reviewing{" "}
          <span className="font-medium text-foreground">
            {workspace.agentName}
          </span>{" "}
          in workspace{" "}
          <span className="font-mono text-xs text-foreground">
            {workspace.workspaceId}
          </span>
          .
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {(workspace?.actions ?? []).map((action) => (
          <CoBuilderPanel
            key={action.id}
            action={action}
            operator={workspace!.operator}
            selectionContext={action.diff.path}
          />
        ))}
      </section>

      {workspace ? (
        <>
          <RubberDuck diagnosis={workspace.rubberDuck} />
          <SecondPairOfEyes review={workspace.review} />
        </>
      ) : null}
    </main>
  );
}
