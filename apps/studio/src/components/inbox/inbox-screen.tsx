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
};

type Reply = { item_id: string; body: string };

export function InboxScreen(props: Props): JSX.Element {
  const [items, setItems] = useState<InboxItem[]>(props.initialItems);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [sentReplies, setSentReplies] = useState<Reply[]>([]);

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

  function handleClaim(item: InboxItem): void {
    const claimed = claimItem(item, {
      operator_id: props.operator_id,
      now_ms: props.now_ms,
    });
    update(claimed);
    setSelectedId(claimed.id);
  }

  function handleRelease(item: InboxItem): void {
    update(releaseItem(item));
    setDraft("");
  }

  function handleSend(item: InboxItem): void {
    if (!draft.trim()) return;
    setSentReplies((r) => [...r, { item_id: item.id, body: draft.trim() }]);
    setDraft("");
  }

  function handleResolve(item: InboxItem): void {
    update(resolveItem(item, { now_ms: props.now_ms }));
    setDraft("");
    setSelectedId(null);
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
                    onClick={() => handleClaim(item)}
                    data-testid={`claim-${item.id}`}
                  >
                    Take over
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
                    onClick={() => handleRelease(selected)}
                    data-testid="release-button"
                  >
                    Release
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                      onClick={() => handleSend(selected)}
                      data-testid="send-button"
                      disabled={!draft.trim()}
                    >
                      Send
                    </button>
                    <button
                      type="button"
                      className="rounded bg-foreground px-3 py-1.5 text-xs font-medium text-background"
                      onClick={() => handleResolve(selected)}
                      data-testid="resolve-button"
                    >
                      Resolve
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
