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

import { fireEvent, waitFor } from "@testing-library/react";

describe("ConversationViewer takeover + composer", () => {
  it("takeover button calls handler and locks ownership to operator", async () => {
    const stub = makeSubscriber();
    let takeoverCalls = 0;
    const takeover = async () => {
      takeoverCalls += 1;
      return { ok: true as const };
    };
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        operator_id="op-1"
        subscribe={stub.subscriber}
        takeover={takeover}
      />,
    );
    const btn = screen.getByTestId("conversation-takeover");
    expect(btn).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(btn);
    });
    await waitFor(() => {
      expect(screen.getByTestId("conversation-owned-badge")).toBeInTheDocument();
    });
    expect(takeoverCalls).toBe(1);
    expect(screen.queryByTestId("conversation-takeover")).toBeNull();
  });

  it("composer is disabled until operator owns the conversation", () => {
    const stub = makeSubscriber();
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        operator_id="op-1"
        subscribe={stub.subscriber}
      />,
    );
    expect(screen.getByTestId("conversation-composer-input")).toBeDisabled();
    expect(screen.getByTestId("conversation-composer-send")).toBeDisabled();
  });

  it("posts a message as the operator and appends it to the transcript", async () => {
    const stub = makeSubscriber();
    const postMessage = async ({
      conversation_id,
      body,
    }: {
      conversation_id: string;
      body: string;
    }) => ({
      ok: true as const,
      message: {
        id: "op-msg-1",
        conversation_id,
        role: "operator" as const,
        body,
        created_at_ms: Date.UTC(2026, 4, 1, 12, 0),
      },
    });
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialOwnership="operator"
        initialTranscript={FIXTURE_TRANSCRIPT}
        operator_id="op-1"
        postMessage={postMessage}
        subscribe={stub.subscriber}
      />,
    );
    const input = screen.getByTestId(
      "conversation-composer-input",
    ) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "Hi, real human here." } });
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-composer-send"));
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("conversation-message-op-msg-1"),
      ).toBeInTheDocument();
    });
    expect(input.value).toBe("");
  });

  it("shows an error when the takeover handler fails", async () => {
    const stub = makeSubscriber();
    const takeover = async () => ({
      ok: false as const,
      error: "already-claimed",
    });
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        initialTranscript={FIXTURE_TRANSCRIPT}
        operator_id="op-1"
        subscribe={stub.subscriber}
        takeover={takeover}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-takeover"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("conversation-error").textContent).toMatch(
        /already-claimed/,
      );
    });
  });
});

describe("ConversationViewer handback", () => {
  it("opens confirmation modal then calls handback handler on confirm", async () => {
    const stub = makeSubscriber();
    let handbackCalls = 0;
    const handback = async () => {
      handbackCalls += 1;
      return { ok: true as const };
    };
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        handback={handback}
        initialOwnership="operator"
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback"));
    });
    expect(
      screen.getByTestId("conversation-handback-modal"),
    ).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback-confirm"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("conversation-takeover")).toBeInTheDocument();
    });
    expect(handbackCalls).toBe(1);
    expect(screen.getByTestId("conversation-toast").textContent).toMatch(
      /Handed back/,
    );
  });

  it("cancel closes the modal without invoking the handler", async () => {
    const stub = makeSubscriber();
    let handbackCalls = 0;
    const handback = async () => {
      handbackCalls += 1;
      return { ok: true as const };
    };
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        handback={handback}
        initialOwnership="operator"
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback"));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback-cancel"));
    });
    expect(screen.queryByTestId("conversation-handback-modal")).toBeNull();
    expect(handbackCalls).toBe(0);
    expect(screen.getByTestId("conversation-owned-badge")).toBeInTheDocument();
  });

  it("shows error toast on handback failure and keeps operator ownership", async () => {
    const stub = makeSubscriber();
    const handback = async () => ({
      ok: false as const,
      error: "network-error",
    });
    render(
      <ConversationViewer
        conversation_id={FIXTURE_CONVERSATION_ID}
        handback={handback}
        initialOwnership="operator"
        initialTranscript={FIXTURE_TRANSCRIPT}
        subscribe={stub.subscriber}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback"));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("conversation-handback-confirm"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("conversation-error").textContent).toMatch(
        /network-error/,
      );
    });
    expect(screen.getByTestId("conversation-owned-badge")).toBeInTheDocument();
  });
});
