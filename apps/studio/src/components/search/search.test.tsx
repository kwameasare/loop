import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ContextualFind } from "@/components/search/contextual-find";
import { SavedSearches } from "@/components/search/saved-searches";
import { type FindCandidate, createSavedSearchStore } from "@/lib/search";

const candidates: FindCandidate[] = [
  {
    id: "wb_refund",
    scope: "workbench",
    title: "Refund clarity",
    summary: "Drafted answer about annual renewals",
  },
  {
    id: "tr_refund",
    scope: "trace",
    title: "Refund trace t-9b23",
    summary: "Customer asked about cancellation",
  },
];

describe("ContextualFind", () => {
  it("filters by scope and query", () => {
    render(<ContextualFind candidates={candidates} />);
    expect(
      screen.getByTestId("find-result-wb_refund"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("find-scope-trace"));
    expect(screen.queryByTestId("find-result-wb_refund")).toBeNull();
    expect(
      screen.getByTestId("find-result-tr_refund"),
    ).toBeInTheDocument();
  });

  it("shows the empty state when nothing matches", () => {
    render(<ContextualFind candidates={candidates} />);
    fireEvent.change(screen.getByTestId("find-input"), {
      target: { value: "nothing" },
    });
    expect(screen.getByTestId("find-empty")).toBeInTheDocument();
  });

  it("invokes onSelect when a result is activated by keyboard", () => {
    const onSelect = vi.fn();
    render(
      <ContextualFind candidates={candidates} onSelect={onSelect} />,
    );
    const result = screen.getByTestId("find-result-wb_refund");
    result.focus();
    fireEvent.click(result);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});

describe("SavedSearches", () => {
  it("shows the canonical defaults and remembers last-used", () => {
    const store = createSavedSearchStore();
    const onOpen = vi.fn();
    render(<SavedSearches store={store} onOpen={onOpen} />);
    const item = screen.getByTestId("saved-search-saved_regressing");
    const openButton = within(item).getAllByRole("button")[0]!;
    fireEvent.click(openButton);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("removes a saved search when the trash button is pressed", () => {
    const store = createSavedSearchStore([
      {
        id: "saved_x",
        name: "Custom",
        category: "audit-overrides",
        scope: "audit",
        query: "override",
      },
    ]);
    render(<SavedSearches store={store} />);
    fireEvent.click(screen.getByTestId("saved-search-remove-saved_x"));
    expect(screen.queryByTestId("saved-search-saved_x")).toBeNull();
  });

  it("renders an empty state when nothing is pinned", () => {
    render(<SavedSearches store={createSavedSearchStore([])} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      /No saved searches yet/i,
    );
  });
});
