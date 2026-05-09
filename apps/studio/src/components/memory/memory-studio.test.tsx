import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  createEmptyMemoryStudioData,
  createMemoryStudioData,
} from "@/lib/memory-studio";

import { MemoryStudio } from "./memory-studio";

describe("MemoryStudio", () => {
  it("renders scopes, memory diff, source trace, retention, and safety flags", () => {
    render(<MemoryStudio data={createMemoryStudioData("agent_support")} />);

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
    expect(screen.getByTestId("memory-policy-panel")).toHaveTextContent(
      "Explicit consent required before durable write",
    );
    expect(screen.getByTestId("memory-policy-user")).toHaveTextContent(
      "Privacy implications before activation",
    );
  });

  it("filters across session, user, episodic, and scratch memory", () => {
    render(<MemoryStudio data={createMemoryStudioData("agent_support")} />);

    fireEvent.click(screen.getByTestId("memory-scope-episodic"));
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
  });

  it("queues deletion for durable memory and explains blocked scratch deletion", () => {
    render(<MemoryStudio data={createMemoryStudioData("agent_support")} />);

    fireEvent.click(screen.getByTestId("memory-delete"));
    expect(screen.getByTestId("memory-delete-notice")).toHaveTextContent(
      "Deletion queued for preferred_language",
    );

    fireEvent.click(screen.getByTestId("memory-entry-mem_scratch_order"));
    expect(screen.getByTestId("memory-delete")).toBeDisabled();
  });

  it("replays with and without memory", () => {
    render(<MemoryStudio data={createMemoryStudioData("agent_support")} />);

    fireEvent.click(screen.getByTestId("memory-replay-without-memory"));
    expect(screen.getByTestId("memory-studio-replay")).toHaveTextContent(
      "asks for language preference again",
    );
    expect(screen.getByTestId("memory-studio-replay")).toHaveTextContent(
      "with-memory=cleared",
    );
  });

  it("approves a memory policy and keeps the hash visible for preflight", async () => {
    const data = createMemoryStudioData("agent_support");
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

  it("renders an empty degraded state with replay controls still visible", () => {
    render(<MemoryStudio data={createEmptyMemoryStudioData("agent_empty")} />);

    expect(screen.getByText("Memory data is empty")).toBeInTheDocument();
    expect(screen.getByText("No memory in this scope")).toBeInTheDocument();
    expect(screen.getByTestId("memory-studio-replay")).toBeInTheDocument();
  });
});
