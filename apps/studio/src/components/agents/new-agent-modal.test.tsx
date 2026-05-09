import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AgentIntakeCreateInput,
  AgentIntakeCreateResult,
} from "@/lib/agent-intake";

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
  fill("new-agent-success-metric", "95% eval pass rate before canary.");
  fill("new-agent-escalation-policy", "Escalate policy conflicts.");
}

function makeCreateIntake(result: Partial<AgentIntakeCreateResult> = {}) {
  return vi.fn(async (_workspaceId: string, input: AgentIntakeCreateInput) => ({
    id: result.id ?? "intake_1",
    workspace_id: "ws_1",
    agent_id: result.agent?.id ?? "agt_new",
    state: "draft_ready" as const,
    creation_path: input.creation_path,
    jobs: [],
    artifact_reports: [],
    intent_map: [],
    contradictions: [],
    sensitive_data_findings: [],
    candidate_tools: [],
    candidate_channels: [],
    candidate_memory_policy: {},
    candidate_eval_cases: [],
    risk_notes: [],
    missing_information: [],
    readiness: {
      score: 74,
      ready: ["Commitment Document drafted"],
      needs_attention: [],
      landing: `/agents/${result.agent?.id ?? "agt_new"}`,
    },
    created_object_refs: {},
    created_by: "owner-1",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    agent: {
      id: result.agent?.id ?? "agt_new",
      name: input.agent_name,
      slug: input.slug,
      description: input.contract.business_responsibility,
      active_version: null,
      updated_at: "2026-05-01T00:00:00Z",
      workspace_id: "ws_1",
    },
    commitment: {
      id: "commit_1",
      agent_id: result.agent?.id ?? "agt_new",
      workspace_id: "ws_1",
      version: 1,
      body: input.contract,
      structured_summary: {
        responsibility: input.contract.business_responsibility,
        audience: input.contract.target_users,
        owner: input.contract.owner_user_id,
        backup_owner: input.contract.backup_owner_user_id,
        risk: input.contract.worst_case_failure,
        channels: input.contract.channels,
        systems_touched: input.contract.systems_touched,
        regions: input.contract.regions,
        languages: input.contract.languages,
        readiness: "complete" as const,
        missing_required_fields: [],
      },
      owner_user_id: input.contract.owner_user_id,
      status: "draft" as const,
      content_hash: "hash",
      created_from: "agent_intake:test",
      created_at: "2026-05-01T00:00:00Z",
      updated_at: "2026-05-01T00:00:00Z",
      accepted_at: null,
      superseded_at: null,
    },
  }));
}

describe("NewAgentModal", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("opens the dialog and submits governed intake, then redirects to the workbench", async () => {
    const createAgentIntake = makeCreateIntake({
      agent: {
        id: "agt_42",
        name: "Sales Bot",
        slug: "sales-bot",
        description: "",
        active_version: null,
        updated_at: "2026-05-01T00:00:00Z",
        workspace_id: "ws_1",
      },
    });
    render(
      <NewAgentModal
        existingSlugs={["support"]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
      />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    expect(screen.getByTestId("new-agent-modal")).toBeInTheDocument();

    fill("new-agent-name", "Sales Bot");
    fill("new-agent-slug", "sales-bot");
    fillContract();
    fill("new-agent-artifact-name", "refund_policy.pdf");
    fill("new-agent-artifact-text", "Always cite the May refund policy.");
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    await waitFor(() => {
      expect(createAgentIntake).toHaveBeenCalledWith(
        "ws_1",
        expect.objectContaining({
          agent_name: "Sales Bot",
          slug: "sales-bot",
          creation_path: "business_intent",
          contract: expect.objectContaining({
            channels: ["web", "whatsapp", "voice"],
            owner_user_id: "maya@acme.test",
          }),
          artifacts: [
            expect.objectContaining({
              name: "refund_policy.pdf",
              text: "Always cite the May refund policy.",
            }),
          ],
        }),
      );
    });
    expect(push).toHaveBeenCalledWith("/agents/agt_42?intake=intake_1");
    expect(screen.queryByTestId("new-agent-modal")).not.toBeInTheDocument();
  });

  it("applies approved enterprise template defaults before submit", async () => {
    const createAgentIntake = makeCreateIntake();
    render(
      <NewAgentModal
        existingSlugs={[]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
      />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    fill("new-agent-name", "Receptionist");
    fill("new-agent-slug", "receptionist");
    fireEvent.click(screen.getByLabelText(/Enterprise template/i));
    fireEvent.change(screen.getByTestId("new-agent-template"), {
      target: { value: "tmpl_voice_receptionist" },
    });
    fill("new-agent-owner", "maya@acme.test");
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    await waitFor(() => {
      expect(createAgentIntake).toHaveBeenCalledWith(
        "ws_1",
        expect.objectContaining({
          creation_path: "enterprise_template",
          template_id: "tmpl_voice_receptionist",
          contract: expect.objectContaining({
            business_responsibility: expect.stringContaining("inbound calls"),
            channels: ["voice", "sms"],
            systems_touched: ["calendar", "crm"],
          }),
          artifacts: [
            expect.objectContaining({
              source_ref: "template/tmpl_voice_receptionist/runbook",
            }),
          ],
        }),
      );
    });
  });

  it("uses workspace approved templates when the catalog endpoint returns them", async () => {
    const createAgentIntake = makeCreateIntake();
    const listAgentIntakeTemplates = vi.fn(async () => ({
      items: [
        {
          id: "tmpl_regulated_support",
          name: "Regulated support",
          summary: "Reviewed template for regulated support.",
          channels: ["telegram", "email"],
          systems_touched: ["case system"],
          contract: {
            business_responsibility: "Resolve regulated support cases.",
            target_users: "Compliance-sensitive customers.",
            worst_case_failure: "Answers regulated questions without citation.",
            channels: ["telegram", "email"],
            systems_touched: ["case system"],
            regions: ["eu-west-2"],
            languages: ["en", "de"],
            success_metric: "98% policy-cited answer pass rate.",
            compliance_domain: "Regulated support",
            expected_volume: "1k turns per month",
            budget_target: "$0.10 per turn",
            out_of_scope: "Legal advice.",
            escalation_policy: "Escalate unsupported claims to compliance.",
          },
          capabilities: ["Answer with policy evidence"],
          artifacts: [
            {
              name: "regulated-support-template.md",
              kind: "runbook" as const,
              text: "Cite policy before every regulated answer.",
              source_ref: "template/tmpl_regulated_support/runbook",
            },
          ],
        },
      ],
    }));
    render(
      <NewAgentModal
        existingSlugs={[]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
        listAgentIntakeTemplates={listAgentIntakeTemplates}
      />,
    );

    fireEvent.click(screen.getByTestId("new-agent-button"));
    await waitFor(() => {
      expect(listAgentIntakeTemplates).toHaveBeenCalledWith("ws_1");
    });
    fireEvent.click(screen.getByLabelText(/Enterprise template/i));
    fill("new-agent-name", "Regulated Agent");
    fill("new-agent-slug", "regulated-agent");
    fill("new-agent-owner", "maya@acme.test");
    fireEvent.click(screen.getByTestId("new-agent-submit"));

    await waitFor(() => {
      expect(createAgentIntake).toHaveBeenCalledWith(
        "ws_1",
        expect.objectContaining({
          creation_path: "enterprise_template",
          template_id: "tmpl_regulated_support",
          contract: expect.objectContaining({
            business_responsibility: "Resolve regulated support cases.",
            channels: ["telegram", "email"],
            systems_touched: ["case system"],
          }),
          capabilities: ["Answer with policy evidence"],
          artifacts: [
            expect.objectContaining({
              source_ref: "template/tmpl_regulated_support/runbook",
            }),
          ],
        }),
      );
    });
  });

  it("blocks submission when slug collides with an existing agent", () => {
    const createAgentIntake = makeCreateIntake();
    render(
      <NewAgentModal
        existingSlugs={["support"]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
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
    expect(createAgentIntake).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("rejects malformed slugs before round-tripping", () => {
    const createAgentIntake = makeCreateIntake();
    render(
      <NewAgentModal
        existingSlugs={[]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
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
    expect(createAgentIntake).not.toHaveBeenCalled();
  });

  it("surfaces a server error and keeps the dialog open", async () => {
    const createAgentIntake = vi.fn(async () => {
      throw new Error("cp-api POST /agent-intakes -> 500");
    });
    render(
      <NewAgentModal
        existingSlugs={[]}
        workspaceId="ws_1"
        createAgentIntake={createAgentIntake}
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
        workspaceId="ws_1"
        createAgentIntake={makeCreateIntake()}
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
