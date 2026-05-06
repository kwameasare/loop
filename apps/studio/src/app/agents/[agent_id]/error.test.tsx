import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AgentDetailError from "./error";

describe("AgentDetailError", () => {
  it("renders the route error through the shared target state kit", () => {
    const reset = vi.fn();
    render(
      <AgentDetailError
        error={Object.assign(new Error("load failed"), { digest: "dig_123" })}
        reset={reset}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Agent could not load");
    expect(screen.getByRole("alert")).toHaveTextContent("dig_123");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reset).toHaveBeenCalledTimes(1);
  });
});
