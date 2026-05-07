"use client";

import { useMemo, useState } from "react";

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
  onClaimItem?: InboxMutation;
  onReleaseItem?: InboxMutation;
  onResolveItem?: InboxMutation;
};

type InboxMutation = (item: InboxItem) => Promise<InboxItem>;

type Reply = { item_id: string; body: string };

export function InboxScreen(props: Props): JSX.Element {
  const [items, setItems] = useState<InboxItem[]>(props.initialItems);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [sentReplies, setSentReplies] = useState<Reply[]>([]);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const pending = useMemo(
    () => listPending(items, props.workspace_id),
    [items, props.workspace_id],
  );
  const myClaims = useMemo(
    () => listClaimedBy(items, props.operator_id),
    [items, props.operator_id],
  );
  const selected = useMemo(
    () => items.find((i) => i.id === selectedId) ?? null,
    [items, selectedId],
  );

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
    setSentReplies((r) => [...r, { item_id: item.id, body: draft.trim() }]);
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
    <section
      className="flex h-full gap-6 p-6"
      data-testid="inbox-screen"
    >
      <aside
        className="w-80 shrink-0 rounded-lg border"
        data-testid="inbox-pending"
      >
        <h2 className="border-b px-4 py-3 text-sm font-semibold">
          Pending ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <p className="text-muted-foreground p-4 text-sm">
            No pending escalations.
          </p>
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
          <p className="text-muted-foreground p-4 text-sm">
            Nothing claimed.
          </p>
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
                  <p className="truncate text-sm font-medium">
                    {item.user_id}
                  </p>
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
            className="border-b px-6 py-3 text-sm text-red-600"
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
              <h2 className="text-lg font-semibold">
                {selected.user_id}
              </h2>
              <p className="text-muted-foreground text-xs">
                Reason: {selected.reason} ·{" "}
                {selected.status === "claimed"
                  ? `claimed ${formatRelativeMs(props.now_ms, selected.claimed_at_ms ?? props.now_ms)}`
                  : selected.status}
              </p>
            </header>
            <div
              className="flex-1 px-6 py-4"
              data-testid="inbox-transcript"
            >
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
