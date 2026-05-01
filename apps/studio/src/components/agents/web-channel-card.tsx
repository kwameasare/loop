"use client";

import { useId, useState } from "react";

import {
  buildEmbedSnippet,
  disableWebChannel as defaultDisable,
  enableWebChannel as defaultEnable,
  type WebChannelBinding,
} from "@/lib/web-channels";

type EnableFn = (agentId: string) => Promise<WebChannelBinding>;
type DisableFn = (agentId: string) => Promise<WebChannelBinding>;
type CopyFn = (text: string) => Promise<void>;

export interface WebChannelCardProps {
  agentId: string;
  initialBinding: WebChannelBinding;
  /** Override clipboard for jsdom tests (writeText is unavailable). */
  copy?: CopyFn;
  /** Override network calls in tests. */
  enable?: EnableFn;
  disable?: DisableFn;
}

type Toast = { kind: "success" | "error"; message: string } | null;

const SCRIPT_PLACEHOLDER =
  '<!-- Enable the web channel to mint a snippet for this agent. -->';

/**
 * Configures the embedded web chat channel for an agent. Enabling the
 * channel mints a public bearer token + a ``<script>`` snippet ops can
 * paste into any page; the same UI lets editors copy the snippet to
 * the clipboard or revoke the binding.
 */
export function WebChannelCard({
  agentId,
  initialBinding,
  copy,
  enable = defaultEnable,
  disable = defaultDisable,
}: WebChannelCardProps) {
  const [binding, setBinding] = useState(initialBinding);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<Toast>(null);
  const tokenId = useId();

  const enabled = binding.status === "enabled" && binding.token != null;
  const snippet = enabled
    ? buildEmbedSnippet({
        agentId,
        token: binding.token ?? "",
      })
    : SCRIPT_PLACEHOLDER;

  async function handleToggle() {
    setBusy(true);
    setToast(null);
    try {
      const next = enabled ? await disable(agentId) : await enable(agentId);
      setBinding(next);
      setToast({
        kind: "success",
        message:
          next.status === "enabled"
            ? "Web channel enabled. Copy the snippet to embed it."
            : "Web channel disabled. Existing tokens are revoked.",
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "Channel update failed.",
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy() {
    if (!enabled) return;
    const writer =
      copy ??
      (typeof navigator !== "undefined" && navigator.clipboard
        ? (text: string) => navigator.clipboard.writeText(text)
        : null);
    if (!writer) {
      setToast({ kind: "error", message: "Clipboard not available." });
      return;
    }
    try {
      await writer(snippet);
      setToast({ kind: "success", message: "Snippet copied to clipboard." });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "Copy failed.",
      });
    }
  }

  return (
    <section
      className="rounded border border-gray-200 p-4 flex flex-col gap-3"
      data-testid="web-channel-card"
      data-status={binding.status}
    >
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Web chat widget</h3>
          <p className="text-xs text-muted-foreground">
            Embed the Loop chat widget on your site. Enable to mint a
            scoped public token.
          </p>
        </div>
        <button
          className="rounded bg-gray-900 text-white text-sm px-3 py-1 disabled:opacity-50"
          data-testid="web-channel-toggle"
          disabled={busy}
          onClick={handleToggle}
          type="button"
        >
          {busy
            ? enabled
              ? "Disabling…"
              : "Enabling…"
            : enabled
              ? "Disable"
              : "Enable"}
        </button>
      </header>

      <div className="flex flex-col gap-1">
        <label
          className="text-xs font-medium text-gray-700"
          htmlFor={tokenId}
        >
          Embed snippet
        </label>
        <textarea
          className="font-mono text-xs rounded border border-gray-200 p-2 bg-gray-50 min-h-[110px]"
          data-testid="web-channel-snippet"
          id={tokenId}
          readOnly
          value={snippet}
        />
        <div className="flex gap-2">
          <button
            className="rounded border border-gray-200 text-xs px-2 py-1 disabled:opacity-50"
            data-testid="web-channel-copy"
            disabled={!enabled}
            onClick={handleCopy}
            type="button"
          >
            Copy snippet
          </button>
          {binding.channelId ? (
            <span
              className="text-xs text-gray-500"
              data-testid="web-channel-id"
            >
              Channel id: {binding.channelId}
            </span>
          ) : null}
        </div>
      </div>

      {toast ? (
        <p
          className={
            toast.kind === "success"
              ? "text-xs text-emerald-700"
              : "text-xs text-red-600"
          }
          data-testid={`web-channel-toast-${toast.kind}`}
          role="status"
        >
          {toast.message}
        </p>
      ) : null}
    </section>
  );
}
