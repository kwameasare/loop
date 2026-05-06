import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AgentsError from "./error";
import AgentsLoading from "./loading";

describe("agents route states", () => {
  it("renders loading through the shared target state kit", () => {
    render(<AgentsLoading />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Agent registry is loading",
    );
    expect(screen.getByTestId("target-state-skeleton")).toBeInTheDocument();
  });

  it("renders errors through the shared target state kit", () => {
    const reset = vi.fn();
    render(
      <AgentsError
        error={Object.assign(new Error("agents failed"), {
          digest: "dig_agents",
        })}
        reset={reset}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Agent registry could not load",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("dig_agents");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reset).toHaveBeenCalledTimes(1);
  });
});
