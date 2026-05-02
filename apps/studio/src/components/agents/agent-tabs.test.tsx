import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AGENT_TABS, AgentTabs } from "./agent-tabs";

describe("AgentTabs", () => {
  it("renders one link per tab pointing at /agents/{id}/{segment}", () => {
    render(<AgentTabs agentId="agt_42" pathname="/agents/agt_42" />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(AGENT_TABS.length);
    expect(tabs[0]).toHaveAttribute("href", "/agents/agt_42");
    expect(tabs[1]).toHaveAttribute("href", "/agents/agt_42/versions");
    expect(tabs[2]).toHaveAttribute("href", "/agents/agt_42/channels");
    expect(tabs[3]).toHaveAttribute("href", "/agents/agt_42/tools");
    expect(tabs[4]).toHaveAttribute("href", "/agents/agt_42/kb");
    expect(tabs[5]).toHaveAttribute("href", "/agents/agt_42/secrets");
  });

  it("marks the overview tab active for the bare agent route", () => {
    render(<AgentTabs agentId="agt_42" pathname="/agents/agt_42" />);
    const overview = screen.getByTestId("agent-tab-overview");
    expect(overview).toHaveAttribute("aria-selected", "true");
    expect(overview).toHaveAttribute("aria-current", "page");
    expect(screen.getByTestId("agent-tab-versions")).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("highlights the active tab from the pathname", () => {
    render(<AgentTabs agentId="agt_42" pathname="/agents/agt_42/versions" />);
    expect(screen.getByTestId("agent-tab-versions")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("agent-tab-overview")).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("treats nested paths as still inside the matching tab", () => {
    render(
      <AgentTabs agentId="agt_42" pathname="/agents/agt_42/tools/some-tool" />,
    );
    expect(screen.getByTestId("agent-tab-tools")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
