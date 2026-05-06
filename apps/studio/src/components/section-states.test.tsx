import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  SectionDegraded,
  SectionError,
  SectionLoading,
  SectionPermissionBlocked,
  SectionStale,
} from "./section-states";

describe("section states", () => {
  it("SectionLoading shows the title and skeleton", () => {
    render(
      <SectionLoading
        title="Costs"
        subtitle="Loading cost and budget state."
        stage="Reading usage records"
      />,
    );
    expect(screen.getByTestId("section-loading")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Costs is loading");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading cost and budget state.",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Reading usage records",
    );
  });

  it("SectionError fires reset on Retry click", () => {
    const reset = vi.fn();
    render(
      <SectionError
        title="Inbox"
        reset={reset}
        error={{ request_id: "req_123" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reset).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent("Inbox could not load");
    expect(screen.getByRole("alert")).toHaveTextContent("req_123");
    expect(screen.getByRole("link", { name: "Report" })).toHaveAttribute(
      "href",
      expect.stringContaining("request_id%3Dreq_123"),
    );
  });

  it("SectionState helpers cover degraded, stale, and permission-blocked states", () => {
    const { rerender } = render(
      <SectionDegraded
        title="Tools"
        evidence="Status page incident loop-status-17"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Tools is degraded");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Status page incident loop-status-17",
    );

    rerender(<SectionStale title="Memory" updatedAt="2026-05-06 11:30 UTC" />);
    expect(screen.getByRole("status")).toHaveTextContent("Memory may be stale");

    rerender(
      <SectionPermissionBlocked
        title="Govern"
        evidence="Policy: production.deploy requires owner"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Permission needed for Govern",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Policy: production.deploy requires owner",
    );
  });
});
