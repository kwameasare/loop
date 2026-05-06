import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AmbientHeartbeat } from "@/components/polish/ambient-heartbeat";
import { CharacterSkeleton } from "@/components/polish/character-skeleton";
import { CompletionMark } from "@/components/polish/completion-mark";
import { EarnedMoment } from "@/components/polish/earned-moment";
import { earnedMomentKey } from "@/lib/polish";

describe("EarnedMoment", () => {
  it("renders once and is anchored to a proof href", () => {
    const fired = new Set<string>();
    render(
      <EarnedMoment
        momentId="first-staging-deploy"
        userId="u_1"
        objectId="agent_42"
        fired={fired}
        proofHref="/deploys/changeset_777"
      />,
    );
    const node = screen.getByTestId("earned-moment-first-staging-deploy");
    expect(node).toHaveAttribute("aria-label", "First staging deploy");
    const proof = screen.getByTestId("earned-moment-proof") as HTMLAnchorElement;
    expect(proof.getAttribute("href")).toBe("/deploys/changeset_777");
  });

  it("returns null when the moment has already fired for the same object", () => {
    const fired = new Set([
      earnedMomentKey("u_1", "first-staging-deploy", "agent_42"),
    ]);
    const { container } = render(
      <EarnedMoment
        momentId="first-staging-deploy"
        userId="u_1"
        objectId="agent_42"
        fired={fired}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("returns null when reduce-polish is on", () => {
    const { container } = render(
      <EarnedMoment
        momentId="canary-100"
        userId="u_1"
        objectId="agent_42"
        fired={new Set()}
        preferences={{ reducePolish: true }}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("uses the static alternative when reduced-motion is on", () => {
    render(
      <EarnedMoment
        momentId="first-turn"
        userId="u_1"
        objectId="agent_42"
        fired={new Set()}
        preferences={{ reducedMotion: true }}
      />,
    );
    expect(screen.getByTestId("earned-moment-first-turn")).toHaveAttribute(
      "data-static",
      "true",
    );
  });
});

describe("AmbientHeartbeat", () => {
  it("renders the empty (silent) state when there is no real beat", () => {
    render(<AmbientHeartbeat source="agent-heartbeat" lastBeatAt={null} />);
    const node = screen.getByTestId("ambient-agent-heartbeat");
    expect(node).toHaveAttribute("data-live", "false");
  });

  it("marks itself live when the source has emitted a beat", () => {
    render(
      <AmbientHeartbeat source="multiplayer-presence" lastBeatAt={Date.now()} />,
    );
    const node = screen.getByTestId("ambient-multiplayer-presence");
    expect(node).toHaveAttribute("data-live", "true");
  });

  it("respects forceStatic and disables the pulse class", () => {
    render(
      <AmbientHeartbeat
        source="activity-ribbon"
        lastBeatAt={Date.now()}
        forceStatic
      />,
    );
    const dot = screen.getByTestId("ambient-dot-activity-ribbon");
    expect(dot.className).not.toContain("motion-safe:animate-pulse");
    expect(dot).toHaveAttribute("data-static", "true");
  });
});

describe("CharacterSkeleton", () => {
  it("renders a trace skeleton with a time axis", () => {
    render(<CharacterSkeleton shape="trace" rows={3} />);
    expect(screen.getByTestId("skeleton-trace")).toBeInTheDocument();
    expect(screen.getByTestId("skeleton-time-axis")).toBeInTheDocument();
    expect(screen.getAllByTestId("skeleton-trace-row")).toHaveLength(3);
  });

  it("renders an eval skeleton that exposes the case count", () => {
    render(<CharacterSkeleton shape="eval" rows={6} />);
    expect(screen.getByTestId("skeleton-case-count").textContent).toContain("6");
  });

  it("renders a chart skeleton with axes", () => {
    render(<CharacterSkeleton shape="chart" rows={5} />);
    expect(screen.getByTestId("skeleton-axes")).toBeInTheDocument();
  });
});

describe("CompletionMark", () => {
  it("renders restrained text + optional proof link", () => {
    render(<CompletionMark label="Deploy promoted" proofHref="/p/1" />);
    const mark = screen.getByTestId("completion-mark");
    expect(mark.textContent).toContain("Deploy promoted");
    expect(screen.getByTestId("completion-mark-proof")).toHaveAttribute(
      "href",
      "/p/1",
    );
  });
});
