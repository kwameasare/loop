import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PublicSharePage from "./page";

vi.mock("@/lib/sharing", async () => {
  const actual = await vi.importActual<typeof import("@/lib/sharing")>(
    "@/lib/sharing",
  );
  return {
    ...actual,
    fetchPublicShare: vi.fn(async () => ({
      id: "share_live_1",
      workspace_id: "ws-1",
      source_type: "trace",
      source_id: "trace_refund_742",
      redactions: ["pii", "secrets"],
      expires_at: "2026-05-13T12:00:00.000Z",
      url: "/share/token_1",
      redaction_banner: "2 redaction categories enforced server-side.",
    })),
  };
});

describe("PublicSharePage", () => {
  it("renders server-redacted share evidence for generated share URLs", async () => {
    render(await PublicSharePage({ params: { token: "token_1" } }));

    expect(screen.getByText("trace · trace_refund_742")).toBeInTheDocument();
    expect(screen.getByText("2 redaction categories enforced server-side.")).toBeInTheDocument();
    expect(screen.getByText("pii")).toBeInTheDocument();
    expect(screen.getByText("secrets")).toBeInTheDocument();
  });
});
