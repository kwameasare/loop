import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { QuickBranchLink } from "@/components/sharing/quick-branch-link";
import { ShareDialog } from "@/components/sharing/share-dialog";

const FROZEN = new Date("2026-05-06T12:00:00Z");
const now = () => FROZEN;

describe("ShareDialog", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;
  const samplePayload =
    "Customer alex@acme.test asked for a refund of $129.99 today.";

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
  });

  it("renders a redaction preview that updates when toggles change", () => {
    render(
      <ShareDialog
        open={true}
        onOpenChange={() => {}}
        artifact="trace"
        artifactId="trace_refund_742"
        samplePayload={samplePayload}
        initialRedactions={["pii"]}
        now={now}
      />,
    );
    expect(screen.getByTestId("share-preview")).toHaveTextContent(
      "[redacted: pii email]",
    );

    fireEvent.click(screen.getByTestId("share-redaction-pricing"));
    expect(screen.getByTestId("share-preview")).toHaveTextContent(
      "[redacted: pricing]",
    );
  });

  it("generates a share link, logs the access, and supports revoke", () => {
    render(
      <ShareDialog
        open={true}
        onOpenChange={() => {}}
        artifact="trace"
        artifactId="trace_refund_742"
        samplePayload={samplePayload}
        now={now}
      />,
    );

    fireEvent.click(screen.getByTestId("share-generate"));
    const url = screen.getByTestId("share-url");
    expect(url.textContent).toMatch(/\/share\/trace\//);
    expect(screen.getByTestId("share-access-log")).toHaveTextContent("viewed");

    fireEvent.click(screen.getByTestId("share-revoke"));
    expect(screen.getByTestId("share-access-log")).toHaveTextContent("revoked");
    expect(screen.getByTestId("share-revoke")).toBeDisabled();
  });

  it("shows backend-required errors for workspace share links", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(
      <ShareDialog
        open={true}
        onOpenChange={() => {}}
        artifact="trace"
        artifactId="trace_refund_742"
        samplePayload={samplePayload}
        workspaceId="ws-1"
        now={now}
      />,
    );

    fireEvent.click(screen.getByTestId("share-generate"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("share-url")).not.toBeInTheDocument();
  });
});

describe("QuickBranchLink", () => {
  it("emits a copy event with the focused review URL", () => {
    const onCopy = vi.fn();
    render(
      <QuickBranchLink
        agentId="agent_support"
        branch="feature/refund"
        onCopy={onCopy}
      />,
    );
    const url = screen.getByTestId("quick-branch-url").textContent;
    expect(url).toContain("/review/agent_support/feature%2Frefund");
    fireEvent.click(screen.getByTestId("quick-branch-copy"));
    expect(onCopy).toHaveBeenCalledWith(url);
  });

  it("hides surfaces when the toggle is turned off", () => {
    render(
      <QuickBranchLink agentId="a" branch="b" />,
    );
    fireEvent.click(screen.getByTestId("quick-branch-toggle-canary"));
    const url = decodeURIComponent(
      screen.getByTestId("quick-branch-url").textContent ?? "",
    );
    expect(url).not.toContain(",canary");
  });
});
