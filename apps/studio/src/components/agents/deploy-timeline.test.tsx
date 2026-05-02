import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeployTimeline } from "./deploy-timeline";
import type { Deployment } from "@/lib/deploys";

function mkDep(overrides: Partial<Deployment>): Deployment {
  return {
    id: "dep_1",
    agentId: "a",
    versionId: "v1",
    status: "canary",
    trafficPercent: 25,
    createdAt: "2025-02-21T12:00:00Z",
    promotedAt: null,
    pausedAt: null,
    rolledBackAt: null,
    notes: null,
    ...overrides,
  };
}

describe("DeployTimeline", () => {
  it("renders rows + current canary/live banners", () => {
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({ id: "d1", status: "canary", trafficPercent: 25 }),
          mkDep({ id: "d2", status: "live", trafficPercent: 75, versionId: "v0" }),
        ]}
      />,
    );
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute("data-status", "canary");
    expect(screen.getByTestId("deploy-current-canary")).toHaveTextContent("25%");
    expect(screen.getByTestId("deploy-current-live")).toHaveTextContent("v0");
  });

  it("disables promote/pause for non-canary rows and rollback for non-live rows", () => {
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "rolled_back" })]}
      />,
    );
    expect(screen.getByTestId("deploy-promote-d1")).toBeDisabled();
    expect(screen.getByTestId("deploy-pause-d1")).toBeDisabled();
    expect(screen.getByTestId("deploy-rollback-d1")).toBeDisabled();
  });

  it("promote replaces the canary row with the live deployment and supersedes prior live", async () => {
    const promote = vi.fn(async () =>
      mkDep({ id: "d1", status: "live", trafficPercent: 100, promotedAt: "now" }),
    );
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[
          mkDep({ id: "d1", status: "canary", trafficPercent: 25 }),
          mkDep({ id: "d2", status: "live", trafficPercent: 75, versionId: "v0" }),
        ]}
        promote={promote}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-promote-d1"));
    });
    expect(promote).toHaveBeenCalledWith("a", "d1");
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute("data-status", "live");
    expect(screen.getByTestId("deploy-row-d2")).toHaveAttribute(
      "data-status",
      "superseded",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent("Promoted");
  });

  it("rollback flips a live deployment and surfaces a toast", async () => {
    const rollback = vi.fn(async () =>
      mkDep({ id: "d1", status: "rolled_back", trafficPercent: 0, rolledBackAt: "now" }),
    );
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "live", trafficPercent: 100 })]}
        rollback={rollback}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-rollback-d1"));
    });
    expect(rollback).toHaveBeenCalledWith("a", "d1");
    expect(screen.getByTestId("deploy-row-d1")).toHaveAttribute(
      "data-status",
      "rolled_back",
    );
    expect(screen.getByTestId("deploy-toast-success")).toHaveTextContent("Rolled back");
  });

  it("surfaces an error toast if the action throws", async () => {
    const pause = vi.fn(async () => {
      throw new Error("boom");
    });
    render(
      <DeployTimeline
        agentId="a"
        initialDeployments={[mkDep({ id: "d1", status: "canary" })]}
        pause={pause}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("deploy-pause-d1"));
    });
    expect(screen.getByTestId("deploy-toast-error")).toHaveTextContent("boom");
  });
});
