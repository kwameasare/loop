"use client";

/**
 * S615: Enterprise IdP Connect Panel.
 *
 * Lets workspace admins paste a metadata URL or upload raw XML to
 * connect a SAML 2.0 Identity Provider.  After a successful POST the
 * status card updates to "Pending verification"; once the tenant
 * completes an ACS round-trip the control plane flips the status to
 * "Connected" (reflected here via the `initialStatus` prop or a
 * re-fetch triggered by the parent page).
 *
 * The submit handler is a prop so tests can inject a fake without
 * mocking fetch.
 */

import { useState } from "react";
import type {
  IdpConnectionResponse,
  IdpConnectionStatus,
  IdpMetadataSource,
} from "@/lib/enterprise";

// ---------------------------------------------------------------------------
// Public interface
// ---------------------------------------------------------------------------

export interface IdpConnectPanelProps {
  /** Current IdP connection state from the server. */
  connection: IdpConnectionResponse;
  /**
   * Called when the user submits the connect form.
   * Should call postIdpMetadata and return the updated connection.
   */
  onConnect: (
    source: IdpMetadataSource,
  ) => Promise<IdpConnectionResponse>;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

type InputMode = "url" | "xml";

const STATUS_BADGE: Record<
  IdpConnectionStatus,
  { label: string; className: string }
> = {
  not_configured: {
    label: "Not configured",
    className: "bg-zinc-100 text-zinc-600",
  },
  pending_verification: {
    label: "Pending verification",
    className: "bg-amber-100 text-amber-700",
  },
  connected: {
    label: "Connected",
    className: "bg-emerald-100 text-emerald-700",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IdpConnectPanel({
  connection: initialConnection,
  onConnect,
}: IdpConnectPanelProps) {
  const [mode, setMode] = useState<InputMode>("url");
  const [metadataUrl, setMetadataUrl] = useState("");
  const [metadataXml, setMetadataXml] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState(initialConnection);

  const badge = STATUS_BADGE[connection.status];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const source: IdpMetadataSource =
      mode === "url" ? { url: metadataUrl } : { xml: metadataXml };

    if (mode === "url" && !metadataUrl.trim()) {
      setError("Metadata URL is required.");
      return;
    }
    if (mode === "xml" && !metadataXml.trim()) {
      setError("Metadata XML is required.");
      return;
    }

    setSubmitting(true);
    try {
      const updated = await onConnect(source);
      setConnection(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to upload metadata.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      data-testid="idp-connect-panel"
      className="flex flex-col gap-6"
    >
      {/* Status card */}
      <div
        data-testid="idp-status-card"
        className="rounded-lg border bg-white p-5"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase text-zinc-500">IdP connection</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">
              SAML 2.0 Identity Provider
            </h2>
            {connection.entity_id && (
              <p
                data-testid="idp-entity-id"
                className="mt-1 text-sm text-zinc-600"
              >
                <span className="font-medium">Entity ID: </span>
                {connection.entity_id}
              </p>
            )}
            {connection.acs_url && (
              <p
                data-testid="idp-acs-url"
                className="mt-1 text-sm text-zinc-600"
              >
                <span className="font-medium">ACS URL: </span>
                {connection.acs_url}
              </p>
            )}
            {connection.connected_at && (
              <p
                data-testid="idp-connected-at"
                className="mt-1 text-xs text-zinc-400"
              >
                Connected {new Date(connection.connected_at).toLocaleString()}
              </p>
            )}
          </div>
          <span
            data-testid="idp-status-badge"
            className={`rounded-full px-3 py-1 text-xs font-medium ${badge.className}`}
          >
            {badge.label}
          </span>
        </div>
      </div>

      {/* Connect form */}
      <div className="rounded-lg border bg-white p-5">
        <h3 className="mb-4 font-medium">Connect IdP</h3>

        {/* Mode toggle */}
        <div
          role="tablist"
          className="mb-4 flex rounded-md border w-fit overflow-hidden"
        >
          <button
            role="tab"
            type="button"
            data-testid="idp-tab-url"
            aria-selected={mode === "url"}
            onClick={() => setMode("url")}
            className={
              "px-4 py-2 text-sm font-medium transition-colors " +
              (mode === "url"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50")
            }
          >
            Paste URL
          </button>
          <button
            role="tab"
            type="button"
            data-testid="idp-tab-xml"
            aria-selected={mode === "xml"}
            onClick={() => setMode("xml")}
            className={
              "px-4 py-2 text-sm font-medium transition-colors " +
              (mode === "xml"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50")
            }
          >
            Upload XML
          </button>
        </div>

        <form
          data-testid="idp-connect-form"
          onSubmit={handleSubmit}
          className="flex flex-col gap-4"
        >
          {mode === "url" ? (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Metadata URL</span>
              <input
                data-testid="idp-metadata-url-input"
                type="url"
                className="rounded-md border bg-background px-2 py-1"
                placeholder="https://idp.example.com/app/saml/metadata"
                value={metadataUrl}
                onChange={(e) => setMetadataUrl(e.target.value)}
              />
            </label>
          ) : (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Metadata XML</span>
              <textarea
                data-testid="idp-metadata-xml-input"
                className="rounded-md border bg-background px-2 py-1 font-mono text-xs"
                rows={8}
                placeholder="Paste your IdP metadata XML here..."
                value={metadataXml}
                onChange={(e) => setMetadataXml(e.target.value)}
              />
            </label>
          )}

          {error && (
            <p
              data-testid="idp-connect-error"
              role="alert"
              className="text-sm text-red-600"
            >
              {error}
            </p>
          )}

          <button
            data-testid="idp-connect-submit"
            type="submit"
            disabled={submitting}
            className="self-start rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Connecting…" : "Connect"}
          </button>
        </form>
      </div>
    </section>
  );
}
