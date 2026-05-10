import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentVersionsPage from "./page";

vi.mock("@/components/agents/edit-history-scrubber", () => ({
  EditHistoryScrubber: () => (
    <section data-testid="edit-history-scrubber">Edit history</section>
  ),
}));

vi.mock("@/components/agents/release-candidate-panel", () => ({
  ReleaseCandidatePanel: () => (
    <section data-testid="release-candidate-panel">Release candidate</section>
  ),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentVersionsPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("shows degraded version evidence when the versions route is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response("missing", { status: 404 }),
    );
    vi.stubGlobal("fetch", fetcher);

    render(await AgentVersionsPage({ params: { agent_id: "agent_versions" } }));

    expect(screen.getByTestId("agent-versions-degraded")).toHaveTextContent(
      "versions route returned 404",
    );
    expect(screen.queryByTestId("agent-versions-empty")).not.toBeInTheDocument();
  });
});
