import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  AgentOverview,
  type AgentOverviewProps,
} from "@/components/agents/agent-overview";

const BASE_PROPS: AgentOverviewProps = {
  id: "ag_1",
  name: "Support Bot",
  description: "Handles tier-1 tickets.",
  model: "gpt-4o-mini",
  lastDeploy: {
    deployed_at: "2025-01-15T10:00:00Z",
    version: 3,
    status: "active",
  },
};

describe("AgentOverview", () => {
  it("renders description text", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Handles tier-1 tickets.",
    );
  });

  it("shows placeholder when description is empty", () => {
    render(<AgentOverview {...BASE_PROPS} description="" />);
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "No description yet.",
    );
  });

  it("renders model identifier", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-model")).toHaveTextContent("gpt-4o-mini");
  });

  it("shows 'Not configured' when model is empty", () => {
    render(<AgentOverview {...BASE_PROPS} model="" />);
    expect(screen.getByTestId("overview-model")).toHaveTextContent("Not configured");
  });

  it("renders last-deploy version", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-deploy-version")).toHaveTextContent("v3");
  });

  it("renders last-deploy status", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    expect(screen.getByTestId("overview-deploy-status")).toHaveTextContent("active");
  });

  it("renders 'Never' when deployed_at is null", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        lastDeploy={{ deployed_at: null, version: null, status: null }}
      />,
    );
    expect(screen.getByTestId("overview-deploy-time")).toHaveTextContent("Never");
  });

  it("omits version row when version is null", () => {
    render(
      <AgentOverview
        {...BASE_PROPS}
        lastDeploy={{ deployed_at: null, version: null, status: null }}
      />,
    );
    expect(screen.queryByTestId("overview-deploy-version")).toBeNull();
  });

  // Edit-description modal
  it("opens edit modal when Edit button is clicked", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    expect(screen.getByTestId("edit-desc-modal")).toBeInTheDocument();
  });

  it("modal textarea is pre-filled with current description", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    const textarea = screen.getByTestId(
      "edit-desc-textarea",
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Handles tier-1 tickets.");
  });

  it("saves updated description and closes modal", () => {
    const onSave = vi.fn();
    render(<AgentOverview {...BASE_PROPS} onDescriptionSave={onSave} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    fireEvent.change(screen.getByTestId("edit-desc-textarea"), {
      target: { value: "Updated copy." },
    });
    fireEvent.click(screen.getByTestId("edit-desc-save"));
    // Modal closed
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
    // Callback called
    expect(onSave).toHaveBeenCalledWith("Updated copy.");
    // Description text updated in DOM
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Updated copy.",
    );
  });

  it("cancel closes modal without updating description", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    fireEvent.change(screen.getByTestId("edit-desc-textarea"), {
      target: { value: "Discarded text" },
    });
    fireEvent.click(screen.getByTestId("edit-desc-cancel"));
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
    expect(screen.getByTestId("overview-description")).toHaveTextContent(
      "Handles tier-1 tickets.",
    );
  });

  it("backdrop click closes modal", () => {
    render(<AgentOverview {...BASE_PROPS} />);
    fireEvent.click(screen.getByTestId("overview-edit-desc-button"));
    fireEvent.click(screen.getByTestId("edit-desc-backdrop"));
    expect(screen.queryByTestId("edit-desc-modal")).toBeNull();
  });
});
