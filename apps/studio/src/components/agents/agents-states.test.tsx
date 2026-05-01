import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentsErrorState, AgentsLoadingState } from "./agents-states";

describe("agent page states", () => {
  it("renders the loading skeleton", () => {
    render(<AgentsLoadingState />);
    expect(screen.getByTestId("agents-loading")).toBeInTheDocument();
  });

  it("renders an error state with retry", () => {
    const onRetry = vi.fn();
    render(<AgentsErrorState onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Agents could not load");
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
