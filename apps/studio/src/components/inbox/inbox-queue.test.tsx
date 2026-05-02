import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InboxQueue } from "./inbox-queue";
import {
  FIXTURE_AGENTS,
  FIXTURE_NOW_MS,
  FIXTURE_QUEUE,
  FIXTURE_TEAMS,
  FIXTURE_WORKSPACE_ID,
} from "@/lib/inbox";

function renderQueue(pageSize = 10) {
  return render(
    <InboxQueue
      agents={FIXTURE_AGENTS}
      initialPageSize={pageSize}
      items={FIXTURE_QUEUE}
      now_ms={FIXTURE_NOW_MS}
      teams={FIXTURE_TEAMS}
      workspace_id={FIXTURE_WORKSPACE_ID}
    />,
  );
}

describe("InboxQueue", () => {
  it("renders rows with last-message preview and a link to detail", () => {
    renderQueue();
    expect(screen.getByTestId("queue-table")).toBeInTheDocument();
    const previews = screen.getAllByTestId(/queue-preview-/);
    expect(previews.length).toBeGreaterThan(0);
    const links = screen.getAllByTestId(/queue-link-/);
    expect(links[0]).toHaveAttribute("href", "/inbox");
  });

  it("filters by team", () => {
    renderQueue(50);
    fireEvent.change(screen.getByTestId("queue-filter-team"), {
      target: { value: "team-care" },
    });
    const totalText = screen.getByTestId("queue-count").textContent ?? "";
    expect(totalText).toMatch(/item/);
    // Every visible row's team chip should be Customer Care.
    const rows = screen.getAllByTestId(/queue-row-/);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(row.textContent).toMatch(/Customer Care/);
    }
  });

  it("filters by channel", () => {
    renderQueue(50);
    fireEvent.change(screen.getByTestId("queue-filter-channel"), {
      target: { value: "voice" },
    });
    const rows = screen.getAllByTestId(/queue-row-/);
    for (const row of rows) {
      expect(row.textContent).toMatch(/voice/);
    }
  });

  it("toggles sort direction when clicking the same column twice", () => {
    renderQueue();
    fireEvent.click(screen.getByTestId("queue-sort-user_id"));
    const ascText = screen.getByTestId("queue-sort-user_id").textContent ?? "";
    expect(ascText).toContain("▼"); // first click on a fresh column => desc
    fireEvent.click(screen.getByTestId("queue-sort-user_id"));
    const descText = screen.getByTestId("queue-sort-user_id").textContent ?? "";
    expect(descText).toContain("▲");
  });

  it("paginates and disables prev on first page", () => {
    renderQueue(10);
    expect(screen.getByTestId("queue-prev")).toBeDisabled();
    fireEvent.click(screen.getByTestId("queue-next"));
    expect(screen.getByTestId("queue-page-indicator").textContent).toMatch(
      /Page 2 of/,
    );
  });
});
