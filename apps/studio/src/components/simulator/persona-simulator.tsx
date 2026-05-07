"use client";

import { useState } from "react";
import { TestTube2, UsersRound } from "lucide-react";

import { ConfidenceMeter, LiveBadge, StatePanel } from "@/components/target";
import {
  PERSONA_SET_LABELS,
  runPersonaSimulation,
  type PersonaSet,
  type PersonaSimulationItem,
} from "@/lib/persona-simulator";
import { cn } from "@/lib/utils";

const PERSONA_SETS: PersonaSet[] = ["first-user", "support-risk", "accessibility"];

function personaLabel(value: string): string {
  return value
    .split("-")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function PersonaSimulatorPanel({ agentId }: { agentId: string }) {
  const [personaSet, setPersonaSet] = useState<PersonaSet>("first-user");
  const [items, setItems] = useState<PersonaSimulationItem[]>([]);
  const [running, setRunning] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function runSuite() {
    setRunning(true);
    setError(null);
    try {
      const result = await runPersonaSimulation(agentId, personaSet);
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Persona run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="persona-simulator-panel"
      aria-labelledby="persona-simulator-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            First-user persona simulator
          </p>
          <h3 className="mt-1 text-sm font-semibold" id="persona-simulator-heading">
            Run persona suite
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Five personas each run ten draft scenarios, grouped by who the agent underserves.
          </p>
        </div>
        <LiveBadge tone={running ? "live" : "staged"} pulse={running}>
          {running ? "running" : "50 scenarios"}
        </LiveBadge>
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium">
          Persona set
          <select
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={personaSet}
            onChange={(event) => setPersonaSet(event.target.value as PersonaSet)}
            data-testid="persona-set-picker"
          >
            {PERSONA_SETS.map((set) => (
              <option key={set} value={set}>
                {PERSONA_SET_LABELS[set]}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="inline-flex h-9 items-center justify-center gap-2 rounded-md border bg-background px-3 text-sm font-medium hover:bg-muted/50 disabled:opacity-60"
          onClick={() => void runSuite()}
          disabled={running}
          data-testid="run-persona-suite"
        >
          <UsersRound className="h-4 w-4" aria-hidden />
          {running ? "Running" : "Run"}
        </button>
      </div>

      {error ? (
        <StatePanel className="mt-4" state="error" title="Persona suite failed">
          {error}
        </StatePanel>
      ) : null}

      {items.length > 0 ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-2" data-testid="persona-results">
          {items.map((item) => {
            const percent = Math.round(item.pass_rate * 100);
            const isSaved = saved.includes(item.candidate_eval_id);
            return (
              <article key={item.persona} className="rounded-md border bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold">
                      {personaLabel(item.persona)}
                    </h4>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.failed_scenarios} failures from {item.scenarios} scenarios
                    </p>
                  </div>
                  <span
                    className={cn(
                      "rounded-md border px-2 py-1 text-xs font-medium",
                      percent >= 90
                        ? "border-success/40 bg-success/5 text-success"
                        : "border-warning/50 bg-warning/5 text-warning",
                    )}
                  >
                    {percent}%
                  </span>
                </div>
                <ConfidenceMeter
                  className="mt-3"
                  value={percent}
                  label="Persona pass rate"
                  evidence={item.evidence_ref}
                />
                <button
                  type="button"
                  className="mt-3 inline-flex min-h-9 w-full items-center justify-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50"
                  onClick={() =>
                    setSaved((current) =>
                      current.includes(item.candidate_eval_id)
                        ? current
                        : [...current, item.candidate_eval_id],
                    )
                  }
                  data-testid={`save-persona-eval-${item.persona}`}
                >
                  <TestTube2 className="h-4 w-4" aria-hidden />
                  {isSaved ? "Eval saved" : "Save failures as eval"}
                </button>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
