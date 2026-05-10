import { describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import { InboxScreen } from "./inbox-screen";
import {
  FIXTURE_INBOX,
  FIXTURE_NOW_MS,
  FIXTURE_OPERATOR_ID,
  FIXTURE_WORKSPACE_ID,
} from "@/lib/inbox";

type ScreenProps = Parameters<typeof InboxScreen>[0];

function renderScreen(overrides: Partial<ScreenProps> = {}) {
  return render(
    <InboxScreen
      initialItems={FIXTURE_INBOX}
      workspace_id={FIXTURE_WORKSPACE_ID}
      operator_id={FIXTURE_OPERATOR_ID}
      now_ms={FIXTURE_NOW_MS}
      {...overrides}
    />,
  );
}

describe("InboxScreen", () => {
  it("renders the pending queue oldest-first with takeover buttons", () => {
    renderScreen();
    const pending = screen.getByTestId("inbox-pending");
    const rows = within(pending).getAllByTestId(/^pending-row-/);
    expect(rows).toHaveLength(3);
    // 44... was created before 22..., which was created before 11...
    expect(rows[0].getAttribute("data-testid")).toBe(
      "pending-row-44444444-4444-4444-4444-444444444444",
    );
    expect(rows[1].getAttribute("data-testid")).toBe(
      "pending-row-22222222-2222-2222-2222-222222222222",
    );
    expect(rows[2].getAttribute("data-testid")).toBe(
      "pending-row-11111111-1111-1111-1111-111111111111",
    );
  });

  it("clicking Take over claims the item and opens the composer", () => {
    renderScreen();
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    expect(screen.getByTestId("composer-input")).toBeInTheDocument();
    expect(screen.getByTestId("resolution-to-eval")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("claim reconciles with the remote inbox endpoint", async () => {
    const onClaimItem = vi.fn().mockResolvedValue({
      ...FIXTURE_INBOX[0],
      status: "claimed",
      operator_id: FIXTURE_OPERATOR_ID,
      claimed_at_ms: FIXTURE_NOW_MS + 50,
    });
    renderScreen({ onClaimItem });
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    expect(screen.getByTestId("composer-input")).toBeInTheDocument();
    await waitFor(() => expect(onClaimItem).toHaveBeenCalledTimes(1));
    expect(onClaimItem).toHaveBeenCalledWith(FIXTURE_INBOX[0]);
  });

  it("failed remote claim rolls the optimistic state back", async () => {
    const onClaimItem = vi.fn().mockRejectedValue(new Error("claim conflict"));
    renderScreen({ onClaimItem });
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("inbox-action-error")).toHaveTextContent(
        "claim conflict",
      ),
    );
    expect(
      screen.getByTestId("pending-row-11111111-1111-1111-1111-111111111111"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
  });

  it("Send pushes a reply into the transcript", () => {
    renderScreen();
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    const input = screen.getByTestId("composer-input");
    fireEvent.change(input, { target: { value: "Hi, this is Alice." } });
    fireEvent.click(screen.getByTestId("send-button"));
    expect(
      screen.getByTestId("reply-11111111-1111-1111-1111-111111111111-0"),
    ).toHaveTextContent("Hi, this is Alice.");
    // Composer cleared.
    expect(
      (screen.getByTestId("composer-input") as HTMLTextAreaElement).value,
    ).toBe("");
  });

  it("saves a claimed operator resolution as an eval with evidence", async () => {
    const onSaveResolutionEval = vi.fn().mockResolvedValue({
      ok: true,
      suite_id: "operator-resolutions",
      case_id: "eval_resolution_1",
    });
    renderScreen({ onSaveResolutionEval });
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    const input = screen.getByTestId("composer-input");
    fireEvent.change(input, {
      target: { value: "I confirmed the May policy and issued the refund." },
    });
    fireEvent.click(screen.getByTestId("send-button"));

    fireEvent.click(screen.getByTestId("resolution-save-eval"));

    await waitFor(() => expect(onSaveResolutionEval).toHaveBeenCalledTimes(1));
    expect(onSaveResolutionEval).toHaveBeenCalledWith(
      expect.objectContaining({
        expectedOutcome: "I confirmed the May policy and issued the refund.",
        failureReason: FIXTURE_INBOX[0].reason,
        linkedTrace: `trace/${FIXTURE_INBOX[0].conversation_id}`,
        source: "operator-resolution",
      }),
    );
    expect(
      await screen.findByTestId("resolution-to-eval-saved"),
    ).toHaveTextContent("operator-resolutions");
    expect(screen.getByTestId("resolution-eval-link")).toHaveAttribute(
      "href",
      "/evals?case_id=eval_resolution_1",
    );
  });

  it("Release returns a claimed item to pending", () => {
    renderScreen();
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    fireEvent.click(screen.getByTestId("release-button"));
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
    // Returns to pending column with same id.
    expect(
      screen.getByTestId("pending-row-11111111-1111-1111-1111-111111111111"),
    ).toBeInTheDocument();
  });

  it("Resolve drops the item from the queue and closes the detail pane", () => {
    renderScreen();
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    fireEvent.click(screen.getByTestId("resolve-button"));
    expect(
      screen.queryByTestId("pending-row-11111111-1111-1111-1111-111111111111"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
    expect(
      screen.getByText("Select a conversation from the queue."),
    ).toBeInTheDocument();
  });

  it("My queue lists items already claimed by the operator", () => {
    renderScreen();
    expect(
      screen.getByTestId("claimed-row-33333333-3333-3333-3333-333333333333"),
    ).toBeInTheDocument();
  });

  it("scopes pending and claimed rows to a focused agent from an evidence link", () => {
    renderScreen({
      focused_agent_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    });

    expect(screen.getByTestId("inbox-focused-agent")).toHaveTextContent(
      "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    );
    expect(
      screen.getByTestId("pending-row-11111111-1111-1111-1111-111111111111"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("claimed-row-33333333-3333-3333-3333-333333333333"),
    ).toBeNull();
  });
});
