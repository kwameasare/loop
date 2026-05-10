import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  FIXTURE_BEHAVIOR_CHANGES,
  FIXTURE_BISECT,
  FIXTURE_SNAPSHOTS,
} from "@/lib/snapshots";

import { RegressionBisect } from "./regression-bisect/regression-bisect";
import { WhatCouldBreak } from "./what-could-break/what-could-break";
import { SnapshotsList } from "../snapshots/snapshots-list";

describe("WhatCouldBreak", () => {
  it("renders top changes ordered by tier and confidence", () => {
    render(<WhatCouldBreak changes={FIXTURE_BEHAVIOR_CHANGES} topK={3} />);
    expect(screen.getByTestId("wcb-row-bc_1")).toBeInTheDocument();
    expect(screen.getByTestId("wcb-row-bc_2")).toBeInTheDocument();
    expect(screen.getByTestId("wcb-row-bc_3")).toBeInTheDocument();
    expect(screen.queryByTestId("wcb-row-bc_5")).toBeNull();
  });

  it("expands a row to show old/new behavior and exemplar transcript", () => {
    render(<WhatCouldBreak changes={FIXTURE_BEHAVIOR_CHANGES} topK={5} />);
    fireEvent.click(screen.getByTestId("wcb-row-bc_1").querySelector("button")!);
    const detail = screen.getByTestId("wcb-detail-bc_1");
    expect(detail.textContent).toContain("Transfers to operator immediately");
    expect(detail.textContent).toContain("tr_001");
  });

  it("calls onInspect when the inspect affordance is clicked", () => {
    const onInspect = vi.fn();
    render(
      <WhatCouldBreak
        changes={FIXTURE_BEHAVIOR_CHANGES}
        topK={5}
        onInspect={onInspect}
      />,
    );
    fireEvent.click(screen.getByTestId("wcb-row-bc_2").querySelector("button")!);
    fireEvent.click(screen.getByTestId("wcb-inspect-bc_2"));
    expect(onInspect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "bc_2" }),
    );
  });

  it("renders empty-state when no changes", () => {
    render(<WhatCouldBreak changes={[]} />);
    expect(screen.getByTestId("what-could-break-empty")).toBeInTheDocument();
  });
});

describe("RegressionBisect", () => {
  it("shows expected vs observed, culprit, and per-step pills", () => {
    render(<RegressionBisect result={FIXTURE_BISECT} />);
    expect(screen.getByTestId("bisect-expected").textContent).toContain(
      "flow.refund.escalate",
    );
    expect(screen.getByTestId("bisect-observed").textContent).toContain(
      "flow.refund.completed",
    );
    expect(screen.getByTestId("bisect-culprit").textContent).toContain(
      "9a3f1b2",
    );
    expect(screen.getByTestId("bisect-step-1a2b3c4").textContent).toContain(
      "pass",
    );
    expect(screen.getByTestId("bisect-step-9a3f1b2").textContent).toContain(
      "regress",
    );
  });

  it("runs live bisect for the selected agent and replaces the displayed result", async () => {
    const runBisect = vi.fn(async () => ({
      ...FIXTURE_BISECT,
      caseId: "case_live_refund",
      culpritCommit: "v24",
      confidence: 88,
      expected: "Behavior last known good at v22.",
      observed: "behavior section changed at v24.",
      steps: [
        {
          commit: "v22",
          ts: "2026-05-10T12:00:00Z",
          status: "pass" as const,
          summary: "Last known green reference.",
          evidenceRef: "bisect/agent_1/case_live_refund/since",
        },
        {
          commit: "v24",
          ts: "2026-05-10T12:01:00Z",
          status: "regress" as const,
          summary: "behavior section: removed Spanish branch.",
          evidenceRef: "bisect/agent_1/case_live_refund/culprit",
        },
      ],
    }));
    render(
      <RegressionBisect
        result={FIXTURE_BISECT}
        agentId="agent_1"
        runBisect={runBisect}
      />,
    );

    fireEvent.change(screen.getByTestId("bisect-case"), {
      target: { value: "case_live_refund" },
    });
    fireEvent.change(screen.getByTestId("bisect-since"), {
      target: { value: "v22" },
    });
    fireEvent.change(screen.getByTestId("bisect-until"), {
      target: { value: "v25" },
    });
    fireEvent.click(screen.getByTestId("bisect-run"));

    expect(await screen.findByText(/Regression bisect · case_live_refund/i))
      .toBeInTheDocument();
    expect(screen.getByTestId("bisect-culprit")).toHaveTextContent("v24");
    expect(runBisect).toHaveBeenCalledWith("agent_1", {
      failing_eval_case_id: "case_live_refund",
      since_ref: "v22",
      until_ref: "v25",
    });
  });
});

describe("SnapshotsList", () => {
  it("shows verified pill, sha, signing key for every snapshot", () => {
    render(<SnapshotsList snapshots={FIXTURE_SNAPSHOTS} />);
    for (const snap of FIXTURE_SNAPSHOTS) {
      expect(
        screen.getByTestId(`snapshot-signature-${snap.id}`).textContent,
      ).toContain("signature verified");
      expect(screen.getByTestId(`snapshot-${snap.id}`).textContent).toContain(
        snap.signingKey,
      );
    }
  });

  it("blocks branching when signature does not verify", () => {
    const tampered = [
      { ...FIXTURE_SNAPSHOTS[0], signature: "sig:tampered" },
    ];
    const onBranch = vi.fn();
    render(<SnapshotsList snapshots={tampered} onBranch={onBranch} />);
    expect(
      screen.getByTestId(`snapshot-signature-${tampered[0].id}`).textContent,
    ).toContain("signature failed");
    expect(
      screen.getByTestId(`snapshot-blocked-${tampered[0].id}`),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId(
        `snapshot-branch-${tampered[0].id}-incident`,
      ),
    ).toBeNull();
    expect(onBranch).not.toHaveBeenCalled();
  });

  it("branches a snapshot for incident, demo, or audit on click", () => {
    const onBranch = vi.fn();
    render(<SnapshotsList snapshots={FIXTURE_SNAPSHOTS} onBranch={onBranch} />);
    const target = FIXTURE_SNAPSHOTS[0];
    fireEvent.click(
      screen.getByTestId(`snapshot-branch-${target.id}-incident`),
    );
    expect(onBranch).toHaveBeenCalledWith(
      expect.objectContaining({ id: target.id }),
      "incident",
    );
    expect(
      screen.getByTestId(`snapshot-branched-${target.id}`).textContent,
    ).toContain("incident");
  });

  it("renders empty state when there are no snapshots", () => {
    render(<SnapshotsList snapshots={[]} />);
    expect(screen.getByTestId("snapshots-empty")).toBeInTheDocument();
  });
});
