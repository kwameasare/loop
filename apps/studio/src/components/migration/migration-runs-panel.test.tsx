import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { localMigrationRun } from "@/lib/migration-runs";
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
  const originalBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const run = localMigrationRun("ws_local");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/migrations/imports") && init?.method === "POST") {
          const body = JSON.parse(String(init.body ?? "{}")) as {
            archive_name?: string;
            source?: string;
            target_agent_name?: string;
          };
          return Response.json(
            {
              ...run,
              source: body.source ?? run.source,
              archive_name: body.archive_name ?? run.archive_name,
              target_agent_name:
                body.target_agent_name ?? run.target_agent_name,
              updated_at: new Date().toISOString(),
            },
            { status: 201 },
          );
        }
        if (url.includes("/cutover/advance")) {
          return Response.json({ ...run, status: "cutover_active" });
        }
        if (url.includes("/cutover/rollback")) {
          return Response.json({ ...run, status: "rolled_back" });
        }
        if (url.endsWith("/migrations/imports")) {
          return Response.json({ items: [] });
        }
        return Response.json({ error: "not found" }, { status: 404 });
      }),
    );
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = originalBaseUrl;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

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

  it("surfaces backend-required errors instead of creating local imports", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    const onCreated = vi.fn();
    render(<MigrationRunsPanel workspaceId="ws_local" onCreated={onCreated} />);

    await screen.findByText(/No migration run yet/i);
    fireEvent.click(screen.getByTestId("migration-create-import"));

    await waitFor(() =>
      expect(screen.getByTestId("migration-run-notice").textContent).toMatch(
        /LOOP_CP_API_BASE_URL is required/i,
      ),
    );
    expect(onCreated).not.toHaveBeenCalled();
    expect(screen.queryByTestId("migration-run-summary")).not.toBeInTheDocument();
  });
});
