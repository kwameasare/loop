"use client";

import { useMemo, useState } from "react";

import { PersonalizedEmptyStateSuggestions } from "@/components/empty-state/personalized-empty-state-suggestions";
import {
  ResolutionToEval,
  type SaveEvalFn,
} from "@/components/inbox/resolution-to-eval";
import {
  DEFAULT_RESOLUTION,
  createEvidenceContextFromConversation,
  type EvidenceContext,
  type ResolutionDraft,
} from "@/lib/inbox-resolution";
import {
  claimItem,
  formatRelativeMs,
  listClaimedBy,
  listPending,
  releaseItem,
  resolveItem,
  type InboxItem,
} from "@/lib/inbox";

type Props = {
  initialItems: InboxItem[];
  workspace_id: string;
  operator_id: string;
  now_ms: number;
  focused_agent_id?: string | undefined;
  onClaimItem?: InboxMutation;
  onReleaseItem?: InboxMutation;
  onResolveItem?: InboxMutation;
  onSaveResolutionEval?: SaveEvalFn;
};

type InboxMutation = (item: InboxItem) => Promise<InboxItem>;

type Reply = { item_id: string; body: string; created_at_ms: number };

function evidenceContextForItem(
  item: InboxItem,
  replies: readonly Reply[],
): EvidenceContext {
  return createEvidenceContextFromConversation({
    conversation_id: item.conversation_id,
    messages: [
      {
        id: `${item.id}:last-user-message`,
        role: "user",
        body: item.last_message_excerpt,
        created_at_ms: item.created_at_ms,
      },
      ...replies.map((reply, index) => ({
        id: `${reply.item_id}:operator-reply-${index + 1}`,
        role: "operator" as const,
        body: reply.body,
        created_at_ms: reply.created_at_ms,
      })),
    ],
  });
}

function resolutionDraftForItem(
  item: InboxItem,
  replies: readonly Reply[],
): ResolutionDraft {
  const latestReply = replies.at(-1)?.body.trim();
  return {
    ...DEFAULT_RESOLUTION,
    expectedOutcome:
      latestReply && latestReply.length > 0
        ? latestReply
        : `Resolve "${item.reason}" with a trace-backed human answer for ${item.user_id}.`,
    failureReason: item.reason,
  };
}

export function InboxScreen(props: Props): JSX.Element {
  const [items, setItems] = useState<InboxItem[]>(props.initialItems);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [sentReplies, setSentReplies] = useState<Reply[]>([]);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const scopedItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.workspace_id === props.workspace_id &&
          (!props.focused_agent_id || item.agent_id === props.focused_agent_id),
      ),
    [items, props.focused_agent_id, props.workspace_id],
  );

  const pending = useMemo(
    () => listPending(scopedItems, props.workspace_id),
    [scopedItems, props.workspace_id],
  );
  const myClaims = useMemo(
    () => listClaimedBy(scopedItems, props.operator_id),
    [scopedItems, props.operator_id],
  );
  const selected = useMemo(
    () => scopedItems.find((i) => i.id === selectedId) ?? null,
    [scopedItems, selectedId],
  );
  const selectedReplies = useMemo(
    () =>
      selected === null
        ? []
        : sentReplies.filter((reply) => reply.item_id === selected.id),
    [selected, sentReplies],
  );
  const selectedEvidence = useMemo(
    () =>
      selected === null
        ? null
        : evidenceContextForItem(selected, selectedReplies),
    [selected, selectedReplies],
  );
  const selectedResolutionDraft = useMemo(
    () =>
      selected === null
        ? null
        : resolutionDraftForItem(selected, selectedReplies),
    [selected, selectedReplies],
  );
  const suggestionAgentId =
    selected?.agent_id ??
    pending[0]?.agent_id ??
    myClaims[0]?.agent_id ??
    items.find((item) => item.workspace_id === props.workspace_id)?.agent_id ??
    "agent_unattributed";

  function update(next: InboxItem): void {
    setItems((prev) => prev.map((i) => (i.id === next.id ? next : i)));
  }

  function errorMessage(err: unknown): string {
    return err instanceof Error
      ? err.message
      : "The inbox action could not be completed.";
  }

  async function handleClaim(item: InboxItem): Promise<void> {
    const claimed = claimItem(item, {
      operator_id: props.operator_id,
      now_ms: props.now_ms,
    });
    update(claimed);
    setSelectedId(claimed.id);
    if (!props.onClaimItem) return;
    setBusyItemId(item.id);
    setActionError(null);
    try {
      const committed = await props.onClaimItem(item);
      update(committed);
      setSelectedId(committed.id);
    } catch (err) {
      update(item);
      setSelectedId(null);
      setActionError(errorMessage(err));
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleRelease(item: InboxItem): Promise<void> {
    const released = releaseItem(item);
    update(released);
    setDraft("");
    if (!props.onReleaseItem) return;
    setBusyItemId(item.id);
    setActionError(null);
    try {
      update(await props.onReleaseItem(item));
    } catch (err) {
      update(item);
      setSelectedId(item.id);
      setActionError(errorMessage(err));
    } finally {
      setBusyItemId(null);
    }
  }

  function handleSend(item: InboxItem): void {
    if (!draft.trim()) return;
    setSentReplies((r) => [
      ...r,
      {
        item_id: item.id,
        body: draft.trim(),
        created_at_ms: props.now_ms + r.length + 1,
      },
    ]);
    setDraft("");
  }

  async function handleResolve(item: InboxItem): Promise<void> {
    const resolved = resolveItem(item, { now_ms: props.now_ms });
    update(resolved);
    setDraft("");
    setSelectedId(null);
    if (!props.onResolveItem) return;
    setBusyItemId(item.id);
    setActionError(null);
    try {
      update(await props.onResolveItem(item));
    } catch (err) {
      update(item);
      setSelectedId(item.id);
      setActionError(errorMessage(err));
    } finally {
      setBusyItemId(null);
    }
  }

  return (
    <section className="flex h-full gap-6 p-6" data-testid="inbox-screen">
      <aside
        className="w-80 shrink-0 rounded-lg border"
        data-testid="inbox-pending"
      >
        {props.focused_agent_id ? (
          <div
            className="border-b bg-info/10 px-4 py-3 text-xs text-info"
            data-testid="inbox-focused-agent"
          >
            Showing escalations for agent{" "}
            <span className="font-semibold">{props.focused_agent_id}</span>.
          </div>
        ) : null}
        <h2 className="border-b px-4 py-3 text-sm font-semibold">
          Pending ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <div className="p-4">
            <p className="text-sm text-muted-foreground">
              No pending escalations.
            </p>
            <PersonalizedEmptyStateSuggestions
              agentId={suggestionAgentId}
              surface="inbox"
            />
          </div>
        ) : (
          <ul>
            {pending.map((item) => (
              <li
                key={item.id}
                className="border-b px-4 py-3 last:border-0"
                data-testid={`pending-row-${item.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {item.user_id}
                    </p>
                    <p className="text-muted-foreground truncate text-xs">
                      {item.reason}
                    </p>
                    <p className="text-muted-foreground mt-1 text-[11px]">
                      {formatRelativeMs(props.now_ms, item.created_at_ms)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded border px-2 py-1 text-xs font-medium hover:bg-accent"
                    onClick={() => void handleClaim(item)}
                    data-testid={`claim-${item.id}`}
                    disabled={busyItemId === item.id}
                    aria-busy={busyItemId === item.id}
                  >
                    {busyItemId === item.id ? "Taking over" : "Take over"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <h2 className="border-b border-t px-4 py-3 text-sm font-semibold">
          My queue ({myClaims.length})
        </h2>
        {myClaims.length === 0 ? (
          <p className="text-muted-foreground p-4 text-sm">Nothing claimed.</p>
        ) : (
          <ul>
            {myClaims.map((item) => (
              <li
                key={item.id}
                className="border-b px-4 py-3 last:border-0"
                data-testid={`claimed-row-${item.id}`}
              >
                <button
                  type="button"
                  className="block w-full text-left"
                  onClick={() => setSelectedId(item.id)}
                >
                  <p className="truncate text-sm font-medium">{item.user_id}</p>
                  <p className="text-muted-foreground truncate text-xs">
                    {item.last_message_excerpt}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <main className="flex-1 rounded-lg border" data-testid="inbox-detail">
        {actionError ? (
          <p
            className="border-b px-6 py-3 text-sm text-destructive"
            role="alert"
            data-testid="inbox-action-error"
          >
            {actionError}
          </p>
        ) : null}
        {selected === null ? (
          <p className="text-muted-foreground p-6 text-sm">
            Select a conversation from the queue.
          </p>
        ) : (
          <div className="flex h-full flex-col">
            <header className="border-b px-6 py-4">
              <h2 className="text-lg font-semibold">{selected.user_id}</h2>
              <p className="text-muted-foreground text-xs">
                Reason: {selected.reason} ·{" "}
                {selected.status === "claimed"
                  ? `claimed ${formatRelativeMs(props.now_ms, selected.claimed_at_ms ?? props.now_ms)}`
                  : selected.status}
              </p>
            </header>
            <div className="flex-1 px-6 py-4" data-testid="inbox-transcript">
              <p className="text-sm">{selected.last_message_excerpt}</p>
              {sentReplies
                .filter((r) => r.item_id === selected.id)
                .map((r, idx) => (
                  <p
                    key={idx}
                    className="mt-3 rounded bg-accent px-3 py-2 text-sm"
                    data-testid={`reply-${selected.id}-${idx}`}
                  >
                    {r.body}
                  </p>
                ))}
            </div>
            {selected.status === "claimed" ? (
              <footer className="border-t p-4">
                {selectedEvidence && selectedResolutionDraft ? (
                  <div className="mb-4">
                    <ResolutionToEval
                      key={`${selected.id}:${selectedReplies.length}`}
                      ctx={selectedEvidence}
                      initialDraft={selectedResolutionDraft}
                      onSave={
                        props.onSaveResolutionEval ??
                        (async () => ({
                          ok: false,
                          error:
                            "Resolution eval saving is unavailable until the workspace eval endpoint is connected.",
                        }))
                      }
                    />
                  </div>
                ) : null}
                <textarea
                  className="w-full rounded border p-2 text-sm"
                  rows={3}
                  placeholder="Reply as a human operator…"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  data-testid="composer-input"
                />
                <div className="mt-2 flex justify-between gap-2">
                  <button
                    type="button"
                    className="rounded border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                    onClick={() => void handleRelease(selected)}
                    data-testid="release-button"
                    disabled={busyItemId === selected.id}
                    aria-busy={busyItemId === selected.id}
                  >
                    {busyItemId === selected.id ? "Releasing" : "Release"}
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                      onClick={() => handleSend(selected)}
                      data-testid="send-button"
                      disabled={!draft.trim() || busyItemId === selected.id}
                    >
                      Send
                    </button>
                    <button
                      type="button"
                      className="rounded bg-foreground px-3 py-1.5 text-xs font-medium text-background"
                      onClick={() => void handleResolve(selected)}
                      data-testid="resolve-button"
                      disabled={busyItemId === selected.id}
                      aria-busy={busyItemId === selected.id}
                    >
                      {busyItemId === selected.id ? "Resolving" : "Resolve"}
                    </button>
                  </div>
                </div>
              </footer>
            ) : null}
          </div>
        )}
      </main>
    </section>
  );
}
