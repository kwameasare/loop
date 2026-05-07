import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReplayWorkbench } from "@/components/replay/replay-workbench";
import { getReplayWorkbenchModel } from "@/lib/replay-workbench";

describe("ReplayWorkbench", () => {
  it("renders replay, persona, property, and scene surfaces", () => {
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    expect(screen.getByTestId("replay-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("production-replay")).toHaveTextContent(
      "Production Replay Against The Future",
    );
    expect(screen.getByTestId("persona-simulator")).toHaveTextContent(
      "First User Persona Simulator",
    );
    expect(screen.getByTestId("conversation-property-tester")).toHaveTextContent(
      "Simulate 100 like this",
    );
    expect(screen.getByTestId("scene-library")).toHaveTextContent(
      "Canonical production conversations",
    );
    expect(screen.getByTestId("cost-of-context-slider")).toBeInTheDocument();
  });

  it("lets a builder promote replay evidence into evals", () => {
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    fireEvent.click(screen.getByRole("button", { name: /save as eval/i }));

    expect(screen.getByText(/queued as a regression eval/i)).toBeInTheDocument();
  });
});
