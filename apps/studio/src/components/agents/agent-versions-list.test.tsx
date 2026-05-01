import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { AgentVersionsList } from "./agent-versions-list";
import type { AgentVersionDetail } from "@/lib/agent-versions";

function makeVersions(n: number): AgentVersionDetail[] {
  return Array.from({ length: n }, (_, i) => {
    const version = n - i;
    return {
      id: `ver_${version}`,
      agent_id: "agt_1",
      version,
      deploy_state: version === n ? "active" : "inactive",
      deployed_at: "2026-04-30T12:00:00Z",
      eval_status: "passed",
      config_json: JSON.stringify({ temperature: version / 10 }, null, 2),
    };
  });
}

describe("AgentVersionsList", () => {
  it("paginates rows at the requested page size", () => {
    render(<AgentVersionsList versions={makeVersions(12)} pageSize={5} />);
    expect(screen.getAllByTestId(/agent-version-row-/)).toHaveLength(5);
    expect(screen.getByTestId("agent-versions-pager")).toHaveTextContent(
      /Page 1 of 3/,
    );

    fireEvent.click(screen.getByTestId("agent-versions-next"));
    expect(screen.getByTestId("agent-versions-pager")).toHaveTextContent(
      /Page 2 of 3/,
    );
    fireEvent.click(screen.getByTestId("agent-versions-next"));
    expect(screen.getByTestId("agent-versions-pager")).toHaveTextContent(
      /Page 3 of 3/,
    );
    expect(
      (screen.getByTestId("agent-versions-next") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("opens the diff modal with config_json vs prior version", () => {
    render(<AgentVersionsList versions={makeVersions(3)} pageSize={5} />);
    fireEvent.click(screen.getByTestId("agent-version-row-2"));
    const modal = screen.getByTestId("diff-viewer-modal");
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveTextContent(/v2/);
    expect(modal).toHaveTextContent(/vs v1/);
    // diff body includes both temperature values
    const body = screen.getByTestId("diff-viewer-body");
    expect(body.textContent).toMatch(/0\.1/);
    expect(body.textContent).toMatch(/0\.2/);
  });

  it("labels the initial version diff explicitly", () => {
    render(<AgentVersionsList versions={makeVersions(3)} pageSize={5} />);
    fireEvent.click(screen.getByTestId("agent-version-row-1"));
    expect(screen.getByTestId("diff-viewer-modal")).toHaveTextContent(
      /initial version/i,
    );
  });

  it("closes the diff modal when Close is pressed", () => {
    render(<AgentVersionsList versions={makeVersions(3)} pageSize={5} />);
    fireEvent.click(screen.getByTestId("agent-version-row-2"));
    fireEvent.click(screen.getByTestId("diff-viewer-close"));
    expect(screen.queryByTestId("diff-viewer-modal")).not.toBeInTheDocument();
  });

  it("renders an empty-state when no versions exist", () => {
    render(<AgentVersionsList versions={[]} />);
    expect(screen.getByTestId("agent-versions-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-versions-list")).not.toBeInTheDocument();
  });
});
