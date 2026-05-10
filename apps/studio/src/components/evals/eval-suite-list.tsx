import Link from "next/link";

import { formatPassRate, type EvalSuite } from "@/lib/evals";

export interface EvalSuiteListProps {
  suites: EvalSuite[];
  focusedSuiteId?: string | undefined;
}

export function EvalSuiteList({ suites, focusedSuiteId }: EvalSuiteListProps) {
  if (suites.length === 0) {
    return (
      <p
        className="text-sm text-muted-foreground"
        data-testid="eval-suites-empty"
      >
        No eval suites have been created yet.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2" data-testid="eval-suites-list">
      {suites.map((suite) => (
        <li
          key={suite.id}
          data-focused={suite.id === focusedSuiteId ? "true" : "false"}
        >
          <Link
            className={`block rounded-md border bg-card p-3 target-transition hover:bg-muted ${
              suite.id === focusedSuiteId
                ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
                : ""
            }`}
            data-testid={`eval-suite-${suite.id}`}
            href={`/evals/suites/${suite.id}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">{suite.name}</span>
              <span className="text-xs text-muted-foreground">
                {suite.cases} cases · pass {formatPassRate(suite.passRate)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              agent: {suite.agentId}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
