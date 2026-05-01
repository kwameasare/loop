import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

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

  it("promotes a version on confirm and updates the row + toast", async () => {
    const promote = vi.fn().mockResolvedValue({
      versionId: "ver_2",
      promoted_to: "production",
      promoted_at: "2026-05-01T00:00:00Z",
    });
    render(
      <AgentVersionsList
        versions={makeVersions(3)}
        pageSize={5}
        promote={promote}
        confirmFn={() => true}
      />,
    );
    expect(screen.getByTestId("agent-version-promoted-2")).toHaveTextContent(
      "—",
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("agent-version-promote-2"));
    });
    expect(promote).toHaveBeenCalledWith({
      versionId: "ver_2",
      stage: "production",
    });
    expect(screen.getByTestId("agent-version-promoted-2")).toHaveTextContent(
      "production",
    );
    expect(screen.getByTestId("promote-toast-success")).toHaveTextContent(
      /v2 promoted to production/i,
    );
  });

  it("skips the request when the user cancels the confirm dialog", () => {
    const promote = vi.fn();
    render(
      <AgentVersionsList
        versions={makeVersions(3)}
        pageSize={5}
        promote={promote}
        confirmFn={() => false}
      />,
    );
    fireEvent.click(screen.getByTestId("agent-version-promote-2"));
    expect(promote).not.toHaveBeenCalled();
  });

  it("shows an error toast when promote fails", async () => {
    const promote = vi
      .fn()
      .mockRejectedValue(new Error("cp-api -> 500"));
    render(
      <AgentVersionsList
        versions={makeVersions(3)}
        pageSize={5}
        promote={promote}
        confirmFn={() => true}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("agent-version-promote-2"));
    });
    expect(screen.getByTestId("promote-toast-error")).toHaveTextContent(
      /Promote failed: cp-api -> 500/,
    );
    // promoted_to stays at em-dash because the call failed
    expect(screen.getByTestId("agent-version-promoted-2")).toHaveTextContent(
      "—",
    );
  });
});
