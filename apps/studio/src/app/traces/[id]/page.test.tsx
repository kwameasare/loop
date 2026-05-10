import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TracePage from "./page";

describe("TracePage", () => {
  it("renders degraded state instead of false not-found when cp-api is unavailable", async () => {
    render(await TracePage({ params: { id: "trace_refund_742" } }));

    expect(screen.getByTestId("trace-page")).toBeInTheDocument();
    expect(screen.getByText("Trace is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/will not replace missing production evidence/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required for trace calls/i),
    ).toBeInTheDocument();
  });
});
