import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvalRunDetailView } from "./eval-run-detail-view";
import type { EvalRunDetail } from "@/lib/evals";

function mkRun(overrides: Partial<EvalRunDetail> = {}): EvalRunDetail {
  return {
    id: "r2",
    suiteId: "s",
    status: "completed",
    startedAt: "2025-01-01T00:00:00Z",
    finishedAt: "2025-01-01T00:01:00Z",
    passed: 1,
    failed: 1,
    errored: 0,
    total: 2,
    baselineRunId: "r1",
    cases: [
      { caseId: "a", name: "regressed", status: "fail", expected: "x", actual: "y", baselineStatus: "pass", durationMs: 100 },
      { caseId: "b", name: "recovered", status: "pass", expected: "x", actual: "x", baselineStatus: "fail", durationMs: 200 },
    ],
    ...overrides,
  };
}

describe("EvalRunDetailView", () => {
  it("highlights regressions vs baseline", () => {
    const baseline: EvalRunDetail = mkRun({
      id: "r1", baselineRunId: null,
      cases: [
        { caseId: "a", name: "regressed", status: "pass", expected: "x", actual: "x", baselineStatus: null, durationMs: 0 },
        { caseId: "b", name: "recovered", status: "fail", expected: "x", actual: "z", baselineStatus: null, durationMs: 0 },
      ],
    });
    render(<EvalRunDetailView run={mkRun()} baseline={baseline} />);
    expect(screen.getByTestId("eval-run-regressions")).toHaveTextContent("Regressions (1)");
    expect(screen.getByTestId("eval-run-recovered")).toHaveTextContent("Recovered (1)");
    expect(screen.getByTestId("eval-case-diff-a")).toHaveTextContent("regression");
    expect(screen.getByTestId("eval-case-diff-b")).toHaveTextContent("recovered");
    expect(screen.getByTestId("eval-run-baseline")).toHaveTextContent("r1");
  });

  it("notes when no baseline is available", () => {
    render(<EvalRunDetailView run={mkRun({ baselineRunId: null })} baseline={null} />);
    expect(screen.getByTestId("eval-run-baseline")).toHaveTextContent("none");
    expect(screen.getByTestId("eval-case-diff-a")).toHaveTextContent("new");
  });
});
