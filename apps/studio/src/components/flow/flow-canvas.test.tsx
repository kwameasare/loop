import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FlowCanvas } from "./flow-canvas";

describe("FlowCanvas", () => {
  it("renders toolbar, viewport and placeholder", () => {
    render(<FlowCanvas agentId="agent-fixture" />);
    expect(screen.getByTestId("flow-toolbar")).toBeInTheDocument();
    expect(screen.getByTestId("flow-viewport")).toBeInTheDocument();
    expect(screen.getByTestId("flow-placeholder")).toBeInTheDocument();
    expect(screen.getByTestId("flow-zoom-pct").textContent).toBe("100%");
  });

  it("zooms in via the toolbar", async () => {
    render(<FlowCanvas agentId="agent-fixture" />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-zoom-in"));
    });
    expect(screen.getByTestId("flow-zoom-pct").textContent).toBe("120%");
  });

  it("reset returns the viewport to 100%", async () => {
    render(<FlowCanvas agentId="agent-fixture" />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-zoom-in"));
      fireEvent.click(screen.getByTestId("flow-zoom-in"));
    });
    expect(screen.getByTestId("flow-zoom-pct").textContent).toBe("144%");
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-reset"));
    });
    expect(screen.getByTestId("flow-zoom-pct").textContent).toBe("100%");
  });

  it("pans the world layer when dragged", async () => {
    render(<FlowCanvas agentId="agent-fixture" />);
    const viewport = screen.getByTestId("flow-viewport");
    await act(async () => {
      fireEvent.mouseDown(viewport, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(viewport, { clientX: 130, clientY: 140 });
      fireEvent.mouseUp(viewport);
    });
    const world = screen.getByTestId("flow-world");
    expect(world.style.transform).toMatch(/translate\(30px, 40px\)/);
  });
});
