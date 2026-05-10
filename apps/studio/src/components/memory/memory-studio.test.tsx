import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  createEmptyMemoryStudioData,
  createMemoryStudioData,
} from "@/lib/memory-studio";
import { targetUxFixtures } from "@/lib/target-ux";

import { MemoryStudio } from "./memory-studio";

describe("MemoryStudio", () => {
  it("renders scopes, memory diff, source trace, retention, and safety flags", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    expect(screen.getByTestId("memory-studio")).toHaveTextContent(
      "Memory Studio",
    );
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "preferred_language",
    );
    expect(screen.getByTestId("memory-studio-diff")).toHaveTextContent(
      "unknown",
    );
    expect(screen.getByTestId("memory-studio-diff")).toHaveTextContent(
      "English",
    );
    expect(screen.getByTestId("memory-studio-detail")).toHaveTextContent(
      "trace_refund_742",
    );
    expect(screen.getByTestId("memory-studio-safety")).toHaveTextContent(
      "durable user preference",
    );
    expect(screen.getByTestId("memory-write-preview")).toHaveTextContent(
      "Memory write preview",
    );
    expect(screen.getByTestId("memory-write-preview")).toHaveTextContent(
      "Proposed value",
    );
    expect(screen.getByTestId("memory-write-preview")).toHaveTextContent(
      "Approve automatically under current policy",
    );
    expect(screen.getByTestId("memory-policy-panel")).toHaveTextContent(
      "Explicit consent required before durable write",
    );
    expect(screen.getByTestId("memory-policy-user")).toHaveTextContent(
      "Privacy implications before activation",
    );
    expect(screen.getByTestId("memory-policy-account")).toHaveTextContent(
      "Account",
    );
    expect(screen.getByTestId("memory-policy-organization")).toHaveTextContent(
      "Organization",
    );
    expect(screen.getByTestId("memory-policy-task")).toHaveTextContent("Task");
    expect(screen.getByTestId("memory-policy-agent")).toHaveTextContent(
      "Agent",
    );
  });

  it("filters across enterprise and runtime memory scopes", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    expect(screen.getByTestId("memory-scope-account")).toBeInTheDocument();
    expect(screen.getByTestId("memory-scope-organization")).toBeInTheDocument();
    expect(screen.getByTestId("memory-scope-task")).toBeInTheDocument();
    expect(screen.getByTestId("memory-scope-agent")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("memory-scope-account"));
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "account_plan_tier",
    );
    expect(screen.getByTestId("memory-studio-explorer")).not.toHaveTextContent(
      "active_order_lookup",
    );

    fireEvent.click(screen.getByTestId("memory-scope-organization"));
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "escalation_contract_owner",
    );

    fireEvent.click(screen.getByTestId("memory-scope-task"));
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "refund_policy_context",
    );
    expect(screen.getByTestId("memory-studio-explorer")).not.toHaveTextContent(
      "active_order_lookup",
    );

    fireEvent.click(screen.getByTestId("memory-scope-scratch"));
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "active_order_lookup",
    );

    fireEvent.click(screen.getByTestId("memory-scope-agent"));
    expect(screen.getByTestId("memory-studio-explorer")).toHaveTextContent(
      "refund_exception_guardrail",
    );
  });

  it("requires backend deletion wiring and explains blocked scratch deletion", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("memory-delete"));
    expect(screen.getByTestId("memory-delete-notice")).toHaveTextContent(
      "Deletion requires cp-api wiring for preferred_language",
    );

    fireEvent.click(screen.getByTestId("memory-entry-mem_scratch_order"));
    expect(screen.getByTestId("memory-delete")).toBeDisabled();
  });

  it("replays with and without memory", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("memory-replay-without-memory"));
    expect(screen.getByTestId("memory-studio-replay")).toHaveTextContent(
      "asks for language preference again",
    );
    expect(screen.getByTestId("memory-studio-replay")).toHaveTextContent(
      "with-memory=cleared",
    );
  });

  it("approves a memory policy and keeps the hash visible for preflight", async () => {
    const data = createMemoryStudioData("agent_support", targetUxFixtures);
    const userPolicy = data.policies.find((policy) => policy.scope === "user")!;
    const approve = vi.fn(async () => ({
      ...userPolicy,
      approval_status: "approved" as const,
      approval_invalidated_at: null,
    }));
    render(<MemoryStudio data={data} onApprovePolicy={approve} />);

    fireEvent.click(screen.getByTestId("memory-policy-approve-user"));

    await waitFor(() => expect(approve).toHaveBeenCalledWith("user"));
    expect(screen.getByTestId("memory-policy-user")).toHaveTextContent(
      "approved",
    );
    expect(screen.getByTestId("memory-policy-notice")).toHaveTextContent(
      "ready for deployment preflight",
    );
  });

  it("focuses a policy opened from an evidence link", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
        initialPolicyId="mp_local_user"
      />,
    );

    expect(screen.getByTestId("memory-focused-policy")).toHaveTextContent(
      "User policy is focused",
    );
    expect(screen.getByTestId("memory-policy-user")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });

  it("focuses memory write, privacy, and retention query states", () => {
    const data = createMemoryStudioData("agent_support", targetUxFixtures);
    const { rerender } = render(
      <MemoryStudio data={data} focusedView="writes" />,
    );

    expect(screen.getByTestId("memory-focused-query")).toHaveTextContent(
      "Memory writes",
    );
    expect(screen.getByTestId("memory-writes-summary")).toHaveClass(
      "ring-focus",
    );

    rerender(<MemoryStudio data={data} focusedFilter="privacy" />);
    expect(screen.getByTestId("memory-focused-query")).toHaveTextContent(
      "Privacy-sensitive memory",
    );
    expect(screen.getByTestId("memory-privacy-summary")).toHaveClass(
      "ring-focus",
    );

    rerender(<MemoryStudio data={data} focusedView="retention" />);
    expect(screen.getByTestId("memory-focused-query")).toHaveTextContent(
      "Retention evidence",
    );
    expect(screen.getByTestId("memory-retention-summary")).toHaveClass(
      "ring-focus",
    );
  });

  it("selects privacy-sensitive memory when opened from privacy evidence", async () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
        focusedFilter="privacy"
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("memory-studio-detail")).toHaveTextContent(
        /pii|secret/i,
      );
    });
  });

  it("saves edited memory policy content before approval", async () => {
    const data = createMemoryStudioData("agent_support", targetUxFixtures);
    const userPolicy = data.policies.find((policy) => policy.scope === "user")!;
    const save = vi.fn(async (input) => ({
      ...userPolicy,
      ...input,
      approval_status: "review_required" as const,
      content_hash: "savedmemoryhash123",
      updated_at: "2026-05-09T00:00:00Z",
    }));
    render(<MemoryStudio data={data} onSavePolicy={save} />);

    fireEvent.change(screen.getByTestId("memory-policy-retention-user"), {
      target: { value: "Keep confirmed preferences for 180 days." },
    });
    fireEvent.change(screen.getByTestId("memory-policy-privacy-user"), {
      target: {
        value: "Affects future conversations, Requires deletion support",
      },
    });
    fireEvent.click(screen.getByTestId("memory-policy-save-user"));

    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        expect.objectContaining({
          scope: "user",
          retention: "Keep confirmed preferences for 180 days.",
          privacy_implications: [
            "Affects future conversations",
            "Requires deletion support",
          ],
          source_trace_required: true,
        }),
      ),
    );
    expect(screen.getByTestId("memory-policy-notice")).toHaveTextContent(
      "policy saved",
    );
    expect(screen.getByTestId("memory-policy-user")).toHaveTextContent(
      "savedmemoryh",
    );
  });

  it("requires backend policy editing wiring when no save action is provided", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("memory-policy-save-user"));

    expect(screen.getByTestId("memory-policy-notice")).toHaveTextContent(
      "User policy editing requires cp-api wiring",
    );
  });

  it("requires backend policy approval wiring when no action is provided", () => {
    render(
      <MemoryStudio
        data={createMemoryStudioData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("memory-policy-approve-user"));

    expect(screen.getByTestId("memory-policy-notice")).toHaveTextContent(
      "User policy approval requires cp-api wiring",
    );
  });

  it("renders an empty degraded state with replay controls still visible", () => {
    const data = createEmptyMemoryStudioData("agent_empty");
    render(<MemoryStudio data={data} />);

    expect(screen.getByText("Memory data is empty")).toBeInTheDocument();
    expect(screen.getByText("No memory in this scope")).toBeInTheDocument();
    expect(screen.getByTestId("memory-studio-replay")).toBeInTheDocument();
    expect(data.agentName).toBe("Agent agent_empty");
    expect(
      screen.queryByText("Acme Support Concierge"),
    ).not.toBeInTheDocument();
  });
});
