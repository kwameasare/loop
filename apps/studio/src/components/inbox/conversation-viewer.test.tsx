import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConversationViewer } from "./conversation-viewer";
import {
  FIXTURE_CONVERSATION_ID,
  FIXTURE_TRANSCRIPT,
  type ConversationMessage,
  type ConversationSubscriber,
} from "@/lib/conversation";

function makeSubscriber() {
  let push: ((m: ConversationMessage) => void) | null = null;
  let unsub = 0;
  const subscriber: ConversationSubscriber = ({ onMessage }) => {
    push = onMessage;
    return {
      unsubscribe: () => {
        unsub += 1;
      },
    };
  };
  return {
    subscriber,
    pushMessage: (m: ConversationMessage) => {
      if (!push) throw new Error("not subscribed");
      push(m);
    },
    get unsubscribeCount() {
      return unsub;
    },
  };
}

describe("ConversationViewer", () => {
  it("renders the initial transcript and live status", () => {
    const stub = makeSubscriber();
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    expect(screen.getByTestId("conversation-message-m1")).toBeInTheDocument();
    expect(screen.getByTestId("conversation-message-m2")).toBeInTheDocument();
    expect(screen.getByTestId("conversation-status").textContent).toMatch(
      /live/,
    );
  });

  it("appends new messages as the SSE stream emits them", async () => {
    const stub = makeSubscriber();
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    await act(async () => {
      stub.pushMessage({
        id: "m4",
        conversation_id: FIXTURE_CONVERSATION_ID,
        role: "operator",
        body: "Hi, I'm taking over now.",
        created_at_ms: Date.UTC(2026, 4, 1, 11, 58),
      });
    });
    expect(screen.getByTestId("conversation-message-m4")).toBeInTheDocument();
    expect(screen.getByTestId("conversation-count").textContent).toMatch(/4/);
  });

  it("dedupes messages with repeated ids", async () => {
    const stub = makeSubscriber();
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    const dup: ConversationMessage = { ...FIXTURE_TRANSCRIPT[1] };
    await act(async () => {
      stub.pushMessage(dup);
    });
    const matches = screen.getAllByTestId(/conversation-message-/);
    expect(matches).toHaveLength(FIXTURE_TRANSCRIPT.length);
  });

  it("unsubscribes on unmount", () => {
    const stub = makeSubscriber();
    const view = render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    view.unmount();
    expect(stub.unsubscribeCount).toBe(1);
  });

  it("renders empty state when transcript is empty", () => {
    const stub = makeSubscriber();
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={[]}
        subscribe={stub.subscriber}
      />,
    );
    expect(screen.getByTestId("conversation-empty")).toBeInTheDocument();
  });
});
