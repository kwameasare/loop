import { describe, expect, it, vi } from "vitest";

import {
  createAgentIntake,
  listAgentIntakeTemplates,
  type AgentIntakeCreateInput,
} from "@/lib/agent-intake";
import { EMPTY_COMMITMENT_BODY } from "@/lib/agent-commitment";

const INPUT: AgentIntakeCreateInput = {
  agent_name: "Billing Support Agent",
  slug: "billing-support",
  creation_path: "business_intent",
  capabilities: ["Answer cancellation questions"],
  artifacts: [
    {
      name: "refund-policy.pdf",
      kind: "pdf",
      text: "Refunds require policy citation.",
      source_ref: "",
    },
  ],
  contract: {
    ...EMPTY_COMMITMENT_BODY,
    business_responsibility: "Resolve billing cancellations safely.",
    target_users: "Enterprise customers.",
    owner_user_id: "maya@acme.test",
    worst_case_failure: "Refund outside policy.",
    channels: ["web", "whatsapp"],
    systems_touched: ["billing"],
    regions: ["us-east-1"],
    languages: ["en"],
  },
};

describe("createAgentIntake", () => {
  it("posts the governed intake payload to cp-api", async () => {
    const fetcher = vi.fn(
      async (
        _url: Parameters<typeof fetch>[0],
        init?: Parameters<typeof fetch>[1],
      ) => {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toMatchObject({
          agent_name: "Billing Support Agent",
          slug: "billing-support",
          creation_path: "business_intent",
        });
        return new Response(
          JSON.stringify({
            id: "intake_1",
            workspace_id: "ws_1",
            agent_id: "agt_1",
            state: "draft_ready",
            creation_path: "business_intent",
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
              score: 82,
              ready: ["Commitment Document drafted"],
              needs_attention: [],
              landing: "/agents/agt_1",
            },
            created_object_refs: {},
            created_by: "owner-1",
            created_at: "2026-05-01T00:00:00Z",
            updated_at: "2026-05-01T00:00:00Z",
            agent: {
              id: "agt_1",
              workspace_id: "ws_1",
              name: "Billing Support Agent",
              slug: "billing-support",
              description: "",
              active_version: null,
              updated_at: "2026-05-01T00:00:00Z",
            },
            commitment: {
              id: "commit_1",
              agent_id: "agt_1",
              workspace_id: "ws_1",
              version: 1,
              body: INPUT.contract,
              structured_summary: {
                responsibility: INPUT.contract.business_responsibility,
                audience: INPUT.contract.target_users,
                owner: INPUT.contract.owner_user_id,
                backup_owner: "",
                risk: INPUT.contract.worst_case_failure,
                channels: INPUT.contract.channels,
                systems_touched: INPUT.contract.systems_touched,
                regions: INPUT.contract.regions,
                languages: INPUT.contract.languages,
                readiness: "complete",
                missing_required_fields: [],
              },
              owner_user_id: INPUT.contract.owner_user_id,
              status: "draft",
              content_hash: "hash",
              created_from: "agent_intake:business_intent",
              created_at: "2026-05-01T00:00:00Z",
              updated_at: "2026-05-01T00:00:00Z",
              accepted_at: null,
              superseded_at: null,
            },
          }),
          { status: 201 },
        );
      },
    ) as unknown as typeof fetch;

    const result = await createAgentIntake("ws_1", INPUT, {
      baseUrl: "https://api.loop.test",
      fetcher,
    });

    expect(result.agent.id).toBe("agt_1");
    expect(result.readiness.score).toBe(82);
  });

  it("falls back to a local governed draft when no base URL exists", async () => {
    const result = await createAgentIntake("local-workspace", INPUT);

    expect(result.state).toBe("draft_ready");
    expect(result.agent.slug).toBe("billing-support");
    expect(result.candidate_eval_cases).toHaveLength(3);
  });
});

describe("listAgentIntakeTemplates", () => {
  it("loads approved template defaults from cp-api", async () => {
    const fetcher = vi.fn(
      async (
        url: Parameters<typeof fetch>[0],
        init?: Parameters<typeof fetch>[1],
      ) => {
        expect(String(url)).toBe(
          "https://api.loop.test/v1/workspaces/ws_1/agent-intake-templates",
        );
        expect(init?.method).toBe("GET");
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "tmpl_regulated_support",
                name: "Regulated support",
                summary: "Reviewed template for regulated support.",
                channels: ["web", "telegram"],
                systems_touched: ["case system"],
                contract: {
                  business_responsibility: "Resolve regulated support cases.",
                  channels: ["web", "telegram"],
                  systems_touched: ["case system"],
                },
                capabilities: ["Answer with policy evidence"],
                artifacts: [
                  {
                    name: "regulated-support-template.md",
                    kind: "runbook",
                    text: "Cite policy before every regulated answer.",
                    source_ref: "template/tmpl_regulated_support/runbook",
                  },
                ],
              },
            ],
          }),
          { status: 200 },
        );
      },
    ) as unknown as typeof fetch;

    const catalog = await listAgentIntakeTemplates("ws_1", {
      baseUrl: "https://api.loop.test",
      fetcher,
    });

    expect(catalog.items[0]).toMatchObject({
      id: "tmpl_regulated_support",
      contract: {
        business_responsibility: "Resolve regulated support cases.",
      },
    });
  });

  it("falls back to local approved templates without a cp-api base URL", async () => {
    const catalog = await listAgentIntakeTemplates("local-workspace");

    expect(catalog.items.map((template) => template.id)).toContain(
      "tmpl_support_agent",
    );
    expect(catalog.items[0]?.contract.channels).toEqual([
      "web",
      "whatsapp",
      "email",
    ]);
  });
});
