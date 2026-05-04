import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SectionError, SectionLoading } from "./section-states";

describe("section states", () => {
  it("SectionLoading shows the title and skeleton", () => {
    const { container } = render(<SectionLoading title="Costs" subtitle="Loading…" />);
    expect(screen.getByTestId("section-loading")).toBeInTheDocument();
    expect(screen.getByText("Costs")).toBeInTheDocument();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(container.firstChild).toMatchSnapshot();
  });

  it("SectionError fires reset on Retry click", () => {
    const reset = vi.fn();
    const { container } = render(
      <SectionError
        title="Inbox"
        reset={reset}
        error={{ request_id: "req_123" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reset).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Inbox could not load",
    );
    expect(screen.getByTestId("section-error-request-id")).toHaveTextContent(
      "request_id: req_123",
    );
    expect(screen.getByTestId("section-error-report")).toHaveAttribute(
      "href",
      expect.stringContaining("request_id%3Dreq_123"),
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
