import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvalSuiteList } from "./eval-suite-list";

describe("EvalSuiteList", () => {
  it("renders suite cards with pass rate", () => {
    render(
      <EvalSuiteList
        suites={[
          {
            id: "evs_1",
            name: "smoke",
            agentId: "a1",
            cases: 10,
            lastRunAt: null,
            passRate: 0.9,
          },
        ]}
      />,
    );
    expect(screen.getByTestId("eval-suite-evs_1")).toHaveTextContent("smoke");
    expect(screen.getByTestId("eval-suite-evs_1")).toHaveTextContent("90%");
  });

  it("marks the suite opened from an evidence link", () => {
    render(
      <EvalSuiteList
        focusedSuiteId="evs_1"
        suites={[
          {
            id: "evs_1",
            name: "smoke",
            agentId: "a1",
            cases: 10,
            lastRunAt: null,
            passRate: 0.9,
          },
        ]}
      />,
    );

    expect(screen.getByTestId("eval-suite-evs_1").parentElement).toHaveAttribute(
      "data-focused",
      "true",
    );
  });

  it("shows empty state", () => {
    render(<EvalSuiteList suites={[]} />);
    expect(screen.getByTestId("eval-suites-empty")).toBeInTheDocument();
  });
});
