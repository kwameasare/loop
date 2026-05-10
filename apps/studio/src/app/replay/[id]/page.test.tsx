import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ReplayPage from "./page";

describe("ReplayPage", () => {
  it("renders degraded state instead of false not-found when trace evidence is unavailable", async () => {
    render(await ReplayPage({ params: { id: "trace_refund_742" } }));

    expect(screen.getByTestId("replay-page")).toBeInTheDocument();
    expect(screen.getByText("Replay is degraded")).toBeInTheDocument();
    expect(
      screen.getByText(/needs the source trace before it can render/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required for trace calls/i),
    ).toBeInTheDocument();
  });
});
