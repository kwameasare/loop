import Link from "next/link";

import { formatPassRate, type EvalSuite } from "@/lib/evals";

export interface EvalSuiteListProps {
  suites: EvalSuite[];
}

export function EvalSuiteList({ suites }: EvalSuiteListProps) {
  if (suites.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="eval-suites-empty">
        No eval suites have been created yet.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2" data-testid="eval-suites-list">
      {suites.map((suite) => (
        <li key={suite.id}>
          <Link
            className="block rounded border border-gray-200 p-3 hover:bg-gray-50"
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
