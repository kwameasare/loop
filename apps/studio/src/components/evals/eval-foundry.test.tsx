import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";

import { EvalFoundry } from "./eval-foundry";
import {
  getEvalFoundryModel,
  type EvalFoundryModel,
  type EvalSuite,
} from "@/lib/evals";

const suites: EvalSuite[] = [
  {
    agentId: "agent_support",
    cases: 18,
    id: "evs_support_smoke",
    lastRunAt: "2026-05-06T08:30:00Z",
    name: "Refund and cancellation parity",
    passRate: 0.96,
  },
];

describe("EvalFoundry", () => {
  it("renders creation sources, suite builder config, and result diffs", () => {
    render(
      <EvalFoundry
        createAction={<button type="button">New suite</button>}
        model={getEvalFoundryModel(suites)}
        suites={suites}
      />,
    );
    expect(screen.getByTestId("eval-creation-sources")).toHaveTextContent(
      "Simulator run",
    );
    expect(screen.getByTestId("eval-creation-sources")).toHaveTextContent(
      "Production conversations",
    );
    expect(screen.getByTestId("eval-creation-sources")).toHaveTextContent(
      "Generated adversarial",
    );
    expect(screen.getByTestId("suite-builder")).toHaveTextContent(
      "Grounded answer",
    );
    expect(screen.getByTestId("suite-builder")).toHaveTextContent(
      "Pass rate >= 95%",
    );
    expect(screen.getByTestId("eval-result-preview")).toHaveTextContent(
      "Before",
    );
    expect(screen.getByTestId("eval-result-preview")).toHaveTextContent(
      "Retrieval",
    );
  });

  it("shows useful empty states for missing suite config and result diffs", () => {
    const model: EvalFoundryModel = {
      creationSources: [],
      featuredResult: null,
      suiteBuilders: [],
    };
    render(
      <EvalFoundry
        createAction={<button type="button">New suite</button>}
        model={model}
        suites={[]}
      />,
    );
    expect(screen.getByText("No case sources yet")).toBeInTheDocument();
    expect(screen.getByText("No suite builder config")).toBeInTheDocument();
    expect(screen.getByText("No result diff yet")).toBeInTheDocument();
  });
});
