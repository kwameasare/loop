/**
 * Memory dashboard tests — S825
 *
 * Tests MemoryTable and MemoryDashboard components:
 * - empty state
 * - renders entries with redacted content
 * - GDPR Art-17 delete button calls onDelete
 * - KPI bar shows correct counts / sizes
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MemoryEntry } from "@/components/memory/memory-table";
import { MemoryTable } from "@/components/memory/memory-table";
import { MemoryDashboard } from "@/components/memory/memory-dashboard";

const ENTRIES: MemoryEntry[] = [
  {
    id: "mem-0001-0000-0000-0000-000000000000",
    agent_id: "agent-alpha",
    user_id: "user-001",
    content: "[REDACTED]",
    created_at: "2025-01-15T10:00:00Z",
    size_bytes: 512,
  },
  {
    id: "mem-0002-0000-0000-0000-000000000000",
    agent_id: "agent-alpha",
    user_id: "user-002",
    content: "[REDACTED]",
    created_at: "2025-01-16T12:00:00Z",
    size_bytes: 2048,
  },
];

// ── MemoryTable ────────────────────────────────────────────────────────────

describe("MemoryTable", () => {
  it("renders empty state when no entries", () => {
    render(<MemoryTable entries={[]} onDelete={vi.fn()} />);
    expect(screen.getByTestId("memory-empty")).toBeDefined();
  });

  it("renders a row for each entry", () => {
    render(<MemoryTable entries={ENTRIES} onDelete={vi.fn()} />);
    const rows = screen.getAllByTestId("memory-row");
    expect(rows).toHaveLength(2);
  });

  it("shows redacted content", () => {
    render(<MemoryTable entries={ENTRIES} onDelete={vi.fn()} />);
    const redacted = screen.getAllByText("[REDACTED]");
    expect(redacted.length).toBeGreaterThan(0);
  });

  it("renders a delete button per row", () => {
    render(<MemoryTable entries={ENTRIES} onDelete={vi.fn()} />);
    const btns = screen.getAllByTestId("memory-delete-btn");
    expect(btns).toHaveLength(2);
  });

  it("calls onDelete with entry id when delete button clicked", () => {
    const onDelete = vi.fn();
    render(<MemoryTable entries={ENTRIES} onDelete={onDelete} />);
    const btns = screen.getAllByTestId("memory-delete-btn");
    fireEvent.click(btns[0]);
    expect(onDelete).toHaveBeenCalledWith(ENTRIES[0].id);
  });

  it("disables delete button for the entry being deleted", () => {
    render(
      <MemoryTable entries={ENTRIES} onDelete={vi.fn()} isDeleting={ENTRIES[1].id} />
    );
    const btns = screen.getAllByTestId("memory-delete-btn");
    expect((btns[1] as HTMLButtonElement).disabled).toBe(true);
    expect((btns[0] as HTMLButtonElement).disabled).toBe(false);
  });

  it("shows 'Deleting…' label for the entry being deleted", () => {
    render(
      <MemoryTable entries={ENTRIES} onDelete={vi.fn()} isDeleting={ENTRIES[0].id} />
    );
    expect(screen.getByText("Deleting…")).toBeDefined();
  });
});

// ── MemoryDashboard ────────────────────────────────────────────────────────

describe("MemoryDashboard", () => {
  it("renders the dashboard container", () => {
    render(
      <MemoryDashboard
        entries={ENTRIES}
        agentId="agent-alpha"
        onDelete={vi.fn()}
      />
    );
    expect(screen.getByTestId("memory-dashboard")).toBeDefined();
  });

  it("shows the agent id in the heading", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    expect(screen.getByTestId("memory-dashboard-heading").textContent).toContain("agent-alpha");
  });

  it("KPI bar shows correct entry count", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    expect(screen.getByTestId("memory-kpi-entries").textContent).toBe("2");
  });

  it("KPI bar shows correct unique user count", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    expect(screen.getByTestId("memory-kpi-users").textContent).toBe("2");
  });

  it("KPI bar shows total size in human-readable form", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    // 512 + 2048 = 2560 B = 2.5 KB
    expect(screen.getByTestId("memory-kpi-size").textContent).toContain("KB");
  });

  it("mentions GDPR Art-17 in the UI", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    expect(screen.getByText(/GDPR Art-17/i)).toBeDefined();
  });

  it("renders MemoryTable inside the dashboard", () => {
    render(
      <MemoryDashboard entries={ENTRIES} agentId="agent-alpha" onDelete={vi.fn()} />
    );
    expect(screen.getByTestId("memory-table")).toBeDefined();
  });
});
