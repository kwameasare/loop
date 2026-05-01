import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), forward: vi.fn() }),
}));

import { NewAgentModal } from "./new-agent-modal";
import type { AgentSummary, CreateAgentInput } from "@/lib/cp-api";

function makeCreate(result: Partial<AgentSummary> = {}) {
  return vi.fn(async (input: CreateAgentInput) => ({
    id: result.id ?? "agt_new",
    name: input.name,
    slug: input.slug,
    description: input.description ?? "",
    active_version: null,
    updated_at: "2026-05-01T00:00:00Z",
    workspace_id: "ws_1",
  }));
}

function fill(testId: string, value: string) {
  fireEvent.change(screen.getByTestId(testId), { target: { value } });
}

describe("NewAgentModal", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("opens the dialog and submits to cp-api, then redirects to the detail page", async () => {
    const createAgent = makeCreate({ id: "agt_42" });
    render(
      <NewAgentModal existingSlugs={["support"]} createAgent={createAgent} />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    expect(screen.getByTestId("new-agent-modal")).toBeInTheDocument();

    fill("new-agent-name", "Sales Bot");
    fill("new-agent-slug", "sales-bot");
    fill("new-agent-description", "Outbound sales agent");
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    await waitFor(() => {
      expect(createAgent).toHaveBeenCalledWith({
        name: "Sales Bot",
        slug: "sales-bot",
        description: "Outbound sales agent",
      });
    });
    expect(push).toHaveBeenCalledWith("/agents/agt_42");
    expect(screen.queryByTestId("new-agent-modal")).not.toBeInTheDocument();
  });

  it("blocks submission when slug collides with an existing agent", () => {
    const createAgent = makeCreate();
    render(
      <NewAgentModal existingSlugs={["support"]} createAgent={createAgent} />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    fill("new-agent-name", "Other Support");
    fill("new-agent-slug", "support");

    expect(screen.getByTestId("new-agent-slug-error")).toHaveTextContent(
      /already exists/i,
    );
    expect(
      (screen.getByTestId("new-agent-submit") as HTMLButtonElement).disabled,
    ).toBe(true);

    fireEvent.click(screen.getByTestId("new-agent-submit"));
    expect(createAgent).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("rejects malformed slugs before round-tripping", () => {
    const createAgent = makeCreate();
    render(<NewAgentModal existingSlugs={[]} createAgent={createAgent} />);

    fireEvent.click(screen.getByTestId("new-agent-button"));
    fill("new-agent-name", "Hi");
    fill("new-agent-slug", "Bad Slug!");

    expect(screen.getByTestId("new-agent-slug-error")).toHaveTextContent(
      /lowercase/i,
    );
    expect(
      (screen.getByTestId("new-agent-submit") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(createAgent).not.toHaveBeenCalled();
  });

  it("surfaces a server error and keeps the dialog open", async () => {
    const createAgent = vi.fn(async () => {
      throw new Error("cp-api POST /agents -> 500");
    });
    render(<NewAgentModal existingSlugs={[]} createAgent={createAgent} />);

    fireEvent.click(screen.getByTestId("new-agent-button"));
    fill("new-agent-name", "Bot");
    fill("new-agent-slug", "bot");
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    expect(await screen.findByTestId("new-agent-error")).toHaveTextContent(
      /500/,
    );
    expect(screen.getByTestId("new-agent-modal")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
