import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import FlowPage from "./page";

describe("legacy agent flow route", () => {
  it("does not mount a flow-builder surface or use forbidden flow-first copy", () => {
    render(<FlowPage params={{ agent_id: "agent_flow" }} />);

    expect(screen.getByTestId("legacy-flow-route")).toHaveTextContent(
      "Legacy route retired",
    );
    expect(screen.getByText("Open Behavior")).toHaveAttribute(
      "href",
      "/agents/agent_flow/behavior",
    );
    expect(screen.getByText("Open Agent Map")).toHaveAttribute(
      "href",
      "/agents/agent_flow/map",
    );
    expect(screen.queryByTestId("flow-placeholder")).toBeNull();
    expect(screen.queryByText(/flow editor/i)).toBeNull();
    expect(screen.queryByText(/flow-first/i)).toBeNull();
  });
});
