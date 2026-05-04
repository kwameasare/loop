import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SectionError, SectionLoading } from "./section-states";

describe("section states", () => {
  it("SectionLoading shows the title and skeleton", () => {
    render(<SectionLoading title="Costs" subtitle="Loading…" />);
    expect(screen.getByTestId("section-loading")).toBeInTheDocument();
    expect(screen.getByText("Costs")).toBeInTheDocument();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("SectionError fires reset on Retry click", () => {
    const reset = vi.fn();
    render(<SectionError title="Inbox" reset={reset} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reset).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Inbox could not load",
    );
  });
});
