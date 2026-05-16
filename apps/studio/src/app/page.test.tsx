import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { deriveEstateHealthFromAgents } from "@/lib/estate-health";

import HomePage from "./home/page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;
const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;
const ORIGINAL_TOKEN = process.env.LOOP_TOKEN;

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("HomePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
    restoreEnv("LOOP_TOKEN", ORIGINAL_TOKEN);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("does not list agents until workspace context is known", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "";

    render(await HomePage());

    expect(screen.getByTestId("home-context-degraded")).toHaveTextContent(
      "Workspace context is required before listing agents.",
    );
    expect(screen.getByTestId("home-context-degraded")).toHaveTextContent(
      "control-plane workspace endpoint",
    );
  });

  it("renders user-scoped pinned work from cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "";
    process.env.LOOP_TOKEN = "test-token";

    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces") {
        return Response.json({
          items: [
            {
              id: "ws_1",
              name: "Acme",
              slug: "acme",
              role: "owner",
            },
          ],
        });
      }
      if (url === "https://cp.test/v1/agents") {
        return Response.json({ items: [] });
      }
      if (url === "https://cp.test/v1/workspaces/ws_1/estate-health") {
        return Response.json(
          deriveEstateHealthFromAgents([], {
            workspaceId: "ws_1",
            dataSource: "live",
          }),
        );
      }
      if (url === "https://cp.test/v1/workspaces/ws_1/homepage/pins") {
        return Response.json({
          items: [
            {
              id: "pin_trace",
              source_type: "trace",
              source_id: "trace_1",
              title: "Worst renewal trace",
              href: "/traces/trace_1",
              created_at: "2026-05-10T12:00:00.000Z",
            },
          ],
        });
      }
      return Response.json({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(await HomePage());

    expect(screen.getByTestId("homepage-pins")).toHaveTextContent("Pinned");
    expect(screen.getByRole("link", { name: /worst renewal trace/i }))
      .toHaveAttribute("href", "/traces/trace_1");
  });
});
