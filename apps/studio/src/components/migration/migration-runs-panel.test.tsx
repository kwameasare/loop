import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { MigrationRunsPanel } from "./migration-runs-panel";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("MigrationRunsPanel", () => {
  it("creates a durable migration import run and exposes parity/cutover controls", async () => {
    const onCreated = vi.fn();
    render(<MigrationRunsPanel workspaceId="ws_local" onCreated={onCreated} />);

    await screen.findByText(/No migration run yet/i);
    fireEvent.change(screen.getByTestId("migration-source-select"), {
      target: { value: "rasa" },
    });
    expect(screen.getByTestId("migration-source-profile")).toHaveTextContent(
      "Domain, NLU, stories",
    );
    expect(screen.getByTestId("migration-archive-input")).toHaveValue(
      "rasa-project.zip",
    );
    fireEvent.click(screen.getByTestId("migration-create-import"));

    await screen.findByTestId("migration-run-summary");
    expect(onCreated).toHaveBeenCalledTimes(1);
    expect(onCreated.mock.calls[0]?.[0]).toMatchObject({ source: "rasa" });
    expect(screen.getByTestId("migration-run-summary").textContent).toContain(
      "Acme Imported Concierge",
    );
    expect(screen.getByTestId("migration-open-parity")).toHaveAttribute(
      "href",
      expect.stringContaining("/migrate/parity?migration_id="),
    );

    fireEvent.click(screen.getByTestId("migration-advance-cutover"));
    await waitFor(() =>
      expect(screen.getByTestId("migration-run-notice").textContent).toMatch(
        /Advanced canary_1pct/i,
      ),
    );

    fireEvent.click(screen.getByTestId("migration-rollback-cutover"));
    await waitFor(() =>
      expect(screen.getByTestId("migration-run-status").textContent).toMatch(
        /rolled back/i,
      ),
    );
  });
});
