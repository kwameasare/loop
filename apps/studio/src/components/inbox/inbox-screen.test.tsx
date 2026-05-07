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
    expect(rows).toHaveLength(2);
    // 22... was created earlier than 11... → renders first.
    expect(rows[0].getAttribute("data-testid")).toBe(
      "pending-row-22222222-2222-2222-2222-222222222222",
    );
    expect(rows[1].getAttribute("data-testid")).toBe(
      "pending-row-11111111-1111-1111-1111-111111111111",
    );
  });

  it("clicking Take over claims the item and opens the composer", () => {
    renderScreen();
    fireEvent.click(
      screen.getByTestId("claim-11111111-1111-1111-1111-111111111111"),
    );
    expect(screen.getByTestId("composer-input")).toBeInTheDocument();
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
});
