import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ConfidenceMeter,
  DiffRibbon,
  EvidenceCallout,
  PermissionBoundary,
  RiskHalo,
  SceneCard,
  SnapshotCard,
  StageStepper,
} from "@/components/target";
import { targetUxFixtures } from "@/lib/target-ux";

describe("target primitives", () => {
  it("renders evidence with confidence and source", () => {
    render(
      <EvidenceCallout
        title="Why this changed"
        source="trace_refund_742"
        confidence={72}
      >
        The newer refund policy ranked above the archived policy.
      </EvidenceCallout>,
    );

    expect(screen.getByText("Why this changed")).toBeInTheDocument();
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "72");
    expect(screen.getByText("Source: trace_refund_742")).toBeInTheDocument();
  });

  it("shows non-color risk and object-state affordances", () => {
    render(
      <RiskHalo level="high">
        <StageStepper
          currentId="canary"
          steps={[
            { id: "draft", label: "Draft", state: "draft" },
            { id: "staged", label: "Staged", state: "staged" },
            { id: "canary", label: "Canary", state: "canary" },
            { id: "production", label: "Production", state: "production" },
          ]}
        />
      </RiskHalo>,
    );

    expect(screen.getByTestId("risk-halo")).toHaveAttribute("data-risk", "high");
    expect(screen.getAllByText("Canary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Production").length).toBeGreaterThan(0);
  });

  it("blocks gated surfaces with friendly precision copy", () => {
    const onRequestAccess = vi.fn();
    render(
      <PermissionBoundary
        allowed={false}
        reason="Production promotion needs Release Manager approval."
        onRequestAccess={onRequestAccess}
      >
        <p>Hidden deploy form</p>
      </PermissionBoundary>,
    );

    expect(screen.queryByText("Hidden deploy form")).not.toBeInTheDocument();
    expect(screen.getByText("Permission needed")).toBeInTheDocument();
    screen.getByRole("button", { name: "Request access" }).click();
    expect(onRequestAccess).toHaveBeenCalledTimes(1);
  });

  it("renders snapshot, scene, diff, and confidence primitives", () => {
    render(
      <div>
        <SnapshotCard snapshot={targetUxFixtures.snapshots[0]!} />
        <SceneCard scene={targetUxFixtures.scenes[0]!} />
        <DiffRibbon
          label="Behavioral diff"
          before="Refund answer cited archived policy."
          after="Refund answer cites the May policy."
        />
        <ConfidenceMeter value={96} label="Parity confidence" />
      </div>,
    );

    expect(screen.getByTestId("snapshot-card")).toBeInTheDocument();
    expect(screen.getByTestId("scene-card")).toBeInTheDocument();
    expect(screen.getByText("Behavioral diff")).toBeInTheDocument();
    expect(screen.getByText("96%")).toBeInTheDocument();
  });
});
