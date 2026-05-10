import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EvalSuitePage from "./page";

describe("EvalSuitePage", () => {
  it("renders degraded state instead of not-found when cp-api is unavailable", async () => {
    render(await EvalSuitePage({ params: { suite_id: "evs_support_smoke" } }));

    expect(screen.getByTestId("eval-suite-page")).toBeInTheDocument();
    expect(screen.getByText("Eval Suite is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/will not show local fixture runs as production evidence/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required to load eval suite details/i),
    ).toBeInTheDocument();
  });
});
