import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
}));

import { NewAgentModal } from "./new-agent-modal";
import type { AgentSummary, CreateAgentInput } from "@/lib/cp-api";
import type { CommitmentDraftInput } from "@/lib/agent-commitment";

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

function fillContract() {
  fill(
    "new-agent-business-responsibility",
    "Resolve billing cancellations safely.",
  );
  fill("new-agent-target-users", "Enterprise customers.");
  fill("new-agent-owner", "maya@acme.test");
  fill("new-agent-worst-case-failure", "Promises a refund outside policy.");
  fill("new-agent-channels", "web, whatsapp, voice");
  fill("new-agent-systems", "billing, crm");
  fill("new-agent-regions", "us-east-1, eu-west-2");
  fill("new-agent-languages", "en, es");
}

function makeSaveCommitment() {
  return vi.fn(async (_agentId: string, _input: CommitmentDraftInput) => ({
    id: "commit_1",
    agent_id: "agt_new",
    workspace_id: "ws_1",
    version: 1,
    body: _input.body,
    structured_summary: {
      responsibility: _input.body.business_responsibility,
      audience: _input.body.target_users,
      owner: _input.body.owner_user_id,
      backup_owner: _input.body.backup_owner_user_id,
      risk: _input.body.worst_case_failure,
      channels: _input.body.channels,
      systems_touched: _input.body.systems_touched,
      regions: _input.body.regions,
      languages: _input.body.languages,
      readiness: "complete" as const,
      missing_required_fields: [],
    },
    owner_user_id: _input.body.owner_user_id,
    status: "draft" as const,
    content_hash: "hash",
    created_from: _input.created_from ?? "studio:test",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    accepted_at: null,
    superseded_at: null,
  }));
}

describe("NewAgentModal", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("opens the dialog and submits to cp-api, then redirects to the detail page", async () => {
    const createAgent = makeCreate({ id: "agt_42" });
    const saveCommitmentDraft = makeSaveCommitment();
    render(
      <NewAgentModal
        existingSlugs={["support"]}
        createAgent={createAgent}
        saveCommitmentDraft={saveCommitmentDraft}
      />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    expect(screen.getByTestId("new-agent-modal")).toBeInTheDocument();

    fill("new-agent-name", "Sales Bot");
    fill("new-agent-slug", "sales-bot");
    fillContract();
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    await waitFor(() => {
      expect(createAgent).toHaveBeenCalledWith({
        name: "Sales Bot",
        slug: "sales-bot",
        description: "Resolve billing cancellations safely.",
      });
    });
    expect(saveCommitmentDraft).toHaveBeenCalledWith(
      "agt_42",
      expect.objectContaining({
        created_from: "studio:new_agent_wizard",
        body: expect.objectContaining({
          channels: ["web", "whatsapp", "voice"],
          owner_user_id: "maya@acme.test",
        }),
      }),
    );
    expect(push).toHaveBeenCalledWith("/agents/agt_42/contract");
    expect(screen.queryByTestId("new-agent-modal")).not.toBeInTheDocument();
  });

  it("blocks submission when slug collides with an existing agent", () => {
    const createAgent = makeCreate();
    render(
      <NewAgentModal
        existingSlugs={["support"]}
        createAgent={createAgent}
        saveCommitmentDraft={makeSaveCommitment()}
      />,
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
    render(
      <NewAgentModal
        existingSlugs={[]}
        createAgent={createAgent}
        saveCommitmentDraft={makeSaveCommitment()}
      />,
    );

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
    render(
      <NewAgentModal
        existingSlugs={[]}
        createAgent={createAgent}
        saveCommitmentDraft={makeSaveCommitment()}
      />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    fill("new-agent-name", "Bot");
    fill("new-agent-slug", "bot");
    fillContract();
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    expect(await screen.findByTestId("new-agent-error")).toHaveTextContent(
      /500/,
    );
    expect(screen.getByTestId("new-agent-modal")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("autofocuses the first field and restores focus to trigger on Escape", async () => {
    render(
      <NewAgentModal
        existingSlugs={[]}
        createAgent={makeCreate()}
        saveCommitmentDraft={makeSaveCommitment()}
      />,
    );

    const trigger = screen.getByTestId("new-agent-button");
    trigger.focus();
    fireEvent.click(trigger);

    const nameInput = await screen.findByTestId("new-agent-name");
    expect(nameInput).toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByTestId("new-agent-modal")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });
});
