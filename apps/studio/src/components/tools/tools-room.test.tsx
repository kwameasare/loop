import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createEmptyToolsRoomData,
  createToolsRoomData,
} from "@/lib/agent-tools";
import { targetUxFixtures } from "@/lib/target-ux";

import { ToolsRoom } from "./tools-room";

describe("ToolsRoom", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
    vi.unstubAllGlobals();
  });

  it("renders catalog, detail, safety, mock/live, usage, cost, and eval coverage", () => {
    render(
      <ToolsRoom
        data={createToolsRoomData("agent_support", [], targetUxFixtures)}
      />,
    );

    expect(screen.getByTestId("tools-room")).toHaveTextContent("Tools Room");
    expect(screen.getByTestId("tools-room-catalog")).toHaveTextContent(
      "lookup_order",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Input schema",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Output schema",
    );
    expect(screen.getByTestId("tools-room-auth")).toHaveTextContent(
      "Secret reference",
    );
    expect(screen.getByTestId("tools-room-contract-fields")).toHaveTextContent(
      "Implementation contract",
    );
    expect(screen.getByTestId("tools-room-contract-fields")).toHaveTextContent(
      "Allowed channels",
    );
    expect(screen.getByTestId("tools-room-contract-fields")).toHaveTextContent(
      "tool.order.lookup with trace span",
    );
    expect(screen.getByTestId("tools-room-safety")).toHaveTextContent(
      "Safety contract",
    );
    expect(screen.getByTestId("tool-enablement-checks")).toHaveTextContent(
      "Enablement checks before live use",
    );
    expect(screen.getByTestId("tool-enablement-schema")).toHaveTextContent(
      "passed",
    );
    expect(screen.getByTestId("tool-enablement-eval")).toHaveTextContent(
      "96% eval coverage",
    );
    expect(screen.getByTestId("tool-enablement-owner")).toHaveTextContent(
      "workspace-builder",
    );
    expect(screen.getByTestId("tool-contract-panel")).toHaveTextContent(
      "Tool contract",
    );
    expect(screen.getByTestId("tool-contract-panel")).toHaveTextContent(
      "sandbox",
    );
    expect(screen.getByTestId("tools-room-mock-live")).toHaveTextContent(
      "Mock and live status",
    );
    expect(
      screen.getByRole("meter", { name: "Eval coverage" }),
    ).toHaveAttribute("aria-valuenow", "96");
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "P95 latency",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "PII sent",
    );
  });

  it("shows production grant boundaries for money-moving tools", () => {
    render(
      <ToolsRoom
        data={createToolsRoomData("agent_support", [], targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("tools-room-catalog-tool_issue_refund"));
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "issue_refund",
    );
    expect(
      screen.getByTestId("tools-room-production-boundary"),
    ).toHaveTextContent("Production grant blocked");
    expect(screen.getByTestId("tools-room-grant-production")).toBeDisabled();
    expect(screen.getByTestId("tool-contract-panel")).toHaveTextContent(
      "max_per_call_cents",
    );
    expect(screen.getByTestId("tool-contract-promote")).toBeEnabled();
  });

  it("opens directly on a tool selected from an evidence link", () => {
    render(
      <ToolsRoom
        data={createToolsRoomData("agent_support", [], targetUxFixtures)}
        initialToolId="tool_issue_refund"
      />,
    );

    expect(screen.getByTestId("tools-room-focused-tool")).toHaveTextContent(
      "issue_refund",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "issue_refund",
    );
  });

  it("promotes the selected durable tool contract live", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const data = createToolsRoomData("agent_support", [], targetUxFixtures);
    const refundContract = data.toolContracts.find(
      (contract) => contract.tool_id === "tool_issue_refund",
    );
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ...refundContract,
        live_status: "approved",
        approval_invalidated_at: null,
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    render(<ToolsRoom data={data} />);

    fireEvent.click(screen.getByTestId("tools-room-catalog-tool_issue_refund"));
    fireEvent.click(screen.getByTestId("tool-contract-promote"));

    expect(await screen.findByText("Live approved")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/tool-contracts/tool_issue_refund/promote",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("saves the selected tool safety questionnaire before live promotion", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const data = createToolsRoomData("agent_support", [], targetUxFixtures);
    const lookupContract = data.toolContracts.find(
      (contract) => contract.tool_id === "tool_lookup_order",
    );
    const fetcher = vi.fn<typeof fetch>(async (_url, init) =>
      Response.json({
        ...lookupContract,
        owner_user_id: "tool-owner@acme.test",
        failure_behavior: "Escalate if lookup returns a transport error.",
        content_hash: "savedhash123456",
        updated_at: "2026-05-09T00:00:00Z",
        ...JSON.parse(String(init?.body ?? "{}")),
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    render(<ToolsRoom data={data} />);

    fireEvent.change(screen.getByTestId("tool-contract-owner"), {
      target: { value: "tool-owner@acme.test" },
    });
    fireEvent.change(screen.getByTestId("tool-contract-failure"), {
      target: { value: "Escalate if lookup returns a transport error." },
    });
    fireEvent.click(screen.getByTestId("tool-contract-save"));

    await waitFor(() =>
      expect(fetcher).toHaveBeenCalledWith(
        "https://cp.test/v1/agents/agent_support/tool-contracts/tool_lookup_order",
        expect.objectContaining({ method: "PUT" }),
      ),
    );
    const body = JSON.parse(
      String((fetcher.mock.calls[0]?.[1] as RequestInit).body),
    );
    expect(body.owner_user_id).toBe("tool-owner@acme.test");
    expect(body.failure_behavior).toBe(
      "Escalate if lookup returns a transport error.",
    );
    expect(body.side_effect_level).toBe("read");
    expect(await screen.findByTestId("tool-contract-saved")).toHaveTextContent(
      "Saved safety questionnaire",
    );
  });

  it("drafts a typed tool from a curl request and redacts auth", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        tool_id: "tool_import_live",
        tool_contract: {
          id: "tc_import_live",
          sandbox_status: "sandbox",
          live_status: "review_required",
          side_effect_level: "money_movement",
          money_movement: true,
        },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    render(
      <ToolsRoom
        data={createToolsRoomData("agent_support", [], targetUxFixtures)}
      />,
    );

    expect(
      screen.getByTestId("tools-room-source-devtools"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tools-room-draft-tool"));
    const draft = screen.getByTestId("tools-room-draft");
    expect(draft).toHaveTextContent("api_example_test");
    expect(draft).toHaveTextContent("Authorization header detected");
    expect(draft).toHaveTextContent("redacted");
    expect(draft).toHaveTextContent("Draft only");
    expect(fetcher).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("tools-room-add-library"));
    const contract = await screen.findByTestId("tools-room-import-contract");
    expect(contract).toHaveTextContent("Sandbox contract: sandbox");
    expect(contract).toHaveTextContent("money caps required");
    expect(draft).not.toHaveTextContent("Bearer <redacted>");
    expect(draft).toHaveTextContent("Added to the draft tool library");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/tools/import",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows backend-required errors instead of adding a local imported tool", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(
      <ToolsRoom
        data={createToolsRoomData("agent_support", [], targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("tools-room-draft-tool"));
    fireEvent.click(screen.getByTestId("tools-room-add-library"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("tools-room-draft")).not.toHaveTextContent(
      "Added to the draft tool library",
    );
  });

  it("renders an empty state with the import flow still available", () => {
    render(<ToolsRoom data={createEmptyToolsRoomData("agent_empty")} />);

    expect(screen.getByText("Tool catalog is empty")).toBeInTheDocument();
    expect(screen.getByText("No tools bound yet")).toBeInTheDocument();
    expect(screen.getByTestId("tools-room-import")).toBeInTheDocument();
  });

  it("shows live tool telemetry when cp-api metrics are present", () => {
    const data = createToolsRoomData(
      "agent_support",
      [
        {
          id: "lookup_order",
          name: "lookup_order",
          kind: "http",
          description: "Look up order state.",
          source: "https://orders.example.test",
        },
      ],
      undefined,
      [],
      undefined,
      [
        {
          tool_id: "lookup_order",
          production_usage_7d: 2,
          success_rate_percent: 50,
          p95_latency_ms: 520,
          retry_rate_percent: 50,
          failed_calls_7d: 1,
          pii_sent_7d: 3,
          last_schema_change_at: "2026-05-10T00:00:00Z",
          measurement_status: "measured",
          evidence_ref: "tool-telemetry/lookup_order/2-calls",
        },
      ],
    );

    render(<ToolsRoom data={data} />);

    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Production tool telemetry connected",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent("2");
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "tool-telemetry/lookup_order/2-calls",
    );
  });

  it("renders imported contract-only tools after refresh", () => {
    const data = createToolsRoomData("agent_support", [], undefined, [
      {
        id: "tc_import",
        workspace_id: "ws",
        agent_id: "agent_support",
        tool_id: "tool_imported",
        name: "stripe_request",
        description: "Drafted from cURL.",
        side_effect_level: "write",
        pii_access: true,
        money_movement: false,
        rate_limits: { per_minute: 60 },
        budget_limits: {},
        sandbox_status: "sandbox",
        live_status: "review_required",
        owner_user_id: "owner@example.test",
        approval_policy_id: "policy-tool-live-review",
        failure_behavior: "Return unavailable.",
        compensation_behavior: "No compensation.",
        content_hash: "hash_import",
        approval_invalidated_at: null,
        created_at: "2026-05-10T00:00:00Z",
        updated_at: "2026-05-10T00:00:00Z",
      },
    ]);

    render(<ToolsRoom data={data} />);

    expect(screen.getByTestId("tools-room-catalog")).toHaveTextContent(
      "stripe_request",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Production tool telemetry pending",
    );
    expect(screen.getByTestId("tools-room-detail")).toHaveTextContent(
      "Not measured",
    );
  });
});
