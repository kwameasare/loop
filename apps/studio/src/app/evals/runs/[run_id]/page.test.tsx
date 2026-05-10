import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EvalRunPage from "./page";

describe("EvalRunPage", () => {
  it("renders degraded state instead of not-found when cp-api is unavailable", async () => {
    render(await EvalRunPage({ params: { run_id: "evr_evs_support_smoke_002" } }));

    expect(screen.getByTestId("eval-run-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Run is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/missing control-plane evidence into a false not-found/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required to load eval run details/i),
    ).toBeInTheDocument();
  });
});
