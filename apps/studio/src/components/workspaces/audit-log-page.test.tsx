import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  AuditLogPage,
  EMPTY_FILTERS,
  type AuditEventRow,
  type AuditLogFilters,
} from "./audit-log-page";

const ROWS: AuditEventRow[] = [
  {
    id: "ev-1",
    occurredAt: "2027-06-15T12:00:00Z",
    actorSub: "auth0|alice",
    action: "workspace.create",
    resourceType: "workspace",
    resourceId: "ws-1",
    ip: "10.0.0.5",
    outcome: "success",
  },
  {
    id: "ev-2",
    occurredAt: "2027-06-15T12:05:00Z",
    actorSub: "auth0|bob",
    action: "workspace.member.add",
    resourceType: "workspace_member",
    resourceId: "auth0|carol",
    ip: "10.0.0.7",
    outcome: "denied",
  },
];

describe("AuditLogPage (S631)", () => {
  it("renders one row per event with action and outcome", () => {
    render(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={50}
        totalCount={ROWS.length}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("audit-row-ev-1")).toBeInTheDocument();
    expect(screen.getByTestId("audit-row-ev-2")).toBeInTheDocument();
    expect(screen.getByTestId("audit-row-outcome-ev-1").textContent).toMatch(
      /success/i,
    );
    expect(screen.getByTestId("audit-row-outcome-ev-2").textContent).toMatch(
      /denied/i,
    );
  });

  it("shows the empty-state row when no events match", () => {
    render(
      <AuditLogPage
        events={[]}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={50}
        totalCount={0}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("audit-log-empty")).toBeInTheDocument();
  });

  it("exposes all 7 filter controls (actor, action, resource, time-from, time-to, ip, outcome)", () => {
    render(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={50}
        totalCount={ROWS.length}
        onPageChange={vi.fn()}
      />,
    );
    const ids = [
      "audit-filter-actor",
      "audit-filter-action",
      "audit-filter-resource",
      "audit-filter-time-from",
      "audit-filter-time-to",
      "audit-filter-ip",
      "audit-filter-outcome",
    ];
    for (const id of ids) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
  });

  it("submits all 7 filter values together when Apply is clicked", () => {
    const onFiltersChange = vi.fn<(f: AuditLogFilters) => void>();
    render(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={onFiltersChange}
        page={1}
        pageSize={50}
        totalCount={ROWS.length}
        onPageChange={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByTestId("audit-filter-actor"), {
      target: { value: "auth0|alice" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-action"), {
      target: { value: "workspace.create" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-resource"), {
      target: { value: "workspace" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-time-from"), {
      target: { value: "2027-06-15T00:00" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-time-to"), {
      target: { value: "2027-06-16T00:00" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-ip"), {
      target: { value: "10.0.0.0/8" },
    });
    fireEvent.change(screen.getByTestId("audit-filter-outcome"), {
      target: { value: "success" },
    });
    fireEvent.click(screen.getByTestId("audit-filters-apply"));

    expect(onFiltersChange).toHaveBeenCalledTimes(1);
    expect(onFiltersChange).toHaveBeenCalledWith({
      actor: "auth0|alice",
      action: "workspace.create",
      resource: "workspace",
      timeFrom: "2027-06-15T00:00",
      timeTo: "2027-06-16T00:00",
      ip: "10.0.0.0/8",
      outcome: "success",
    });
  });

  it("resets to EMPTY_FILTERS when Reset is clicked", () => {
    const onFiltersChange = vi.fn();
    render(
      <AuditLogPage
        events={ROWS}
        filters={{ ...EMPTY_FILTERS, actor: "auth0|alice" }}
        onFiltersChange={onFiltersChange}
        page={1}
        pageSize={50}
        totalCount={ROWS.length}
        onPageChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("audit-filters-reset"));
    expect(onFiltersChange).toHaveBeenCalledWith(EMPTY_FILTERS);
  });

  it("disables Previous on page 1 and Next on the last page", () => {
    const { rerender } = render(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={2}
        totalCount={4}
        onPageChange={vi.fn()}
      />,
    );
    expect(
      (screen.getByTestId("audit-page-prev") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("audit-page-next") as HTMLButtonElement).disabled,
    ).toBe(false);

    rerender(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={2}
        pageSize={2}
        totalCount={4}
        onPageChange={vi.fn()}
      />,
    );
    expect(
      (screen.getByTestId("audit-page-prev") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("audit-page-next") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("calls onPageChange with the new page number when navigation is clicked", () => {
    const onPageChange = vi.fn();
    render(
      <AuditLogPage
        events={ROWS}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={2}
        pageSize={2}
        totalCount={6}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByTestId("audit-page-next"));
    expect(onPageChange).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByTestId("audit-page-prev"));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("shows the loading row when loading=true", () => {
    render(
      <AuditLogPage
        events={[]}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={50}
        totalCount={0}
        onPageChange={vi.fn()}
        loading
      />,
    );
    expect(screen.getByTestId("audit-log-loading")).toBeInTheDocument();
  });

  it("surfaces the parent errorMessage", () => {
    render(
      <AuditLogPage
        events={[]}
        filters={EMPTY_FILTERS}
        onFiltersChange={vi.fn()}
        page={1}
        pageSize={50}
        totalCount={0}
        onPageChange={vi.fn()}
        errorMessage="cp-api 500: audit query failed"
      />,
    );
    expect(screen.getByTestId("audit-log-error").textContent).toMatch(/500/);
  });
});
