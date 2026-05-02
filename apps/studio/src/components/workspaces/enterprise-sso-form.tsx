"use client";

/**
 * S615: Enterprise SSO connect form.
 *
 * Lets a workspace admin connect a SAML IdP by either pasting an
 * IdP metadata URL or uploading the IdP metadata XML. Upon submit
 * the parent route POSTs to ``/v1/workspaces/{id}/sso`` (cp-api,
 * S617 plumbing); the visible status badge is driven by the parent
 * and flips to ``connected`` after a successful ACS round-trip.
 *
 * The component is intentionally pure UI: it owns no network or
 * auth state. The page route owns the cp-api client and the polling
 * for ACS confirmation, keeping this component testable in
 * isolation without faking ``fetch``.
 */

import { useState } from "react";

export type SsoStatus = "not_connected" | "pending" | "connected" | "error";

export interface EnterpriseSsoSubmitPayload {
  metadataUrl?: string;
  metadataXml?: string;
}

export interface EnterpriseSsoFormProps {
  status: SsoStatus;
  onSubmit: (payload: EnterpriseSsoSubmitPayload) => Promise<void> | void;
  /** Optional error message surfaced from the parent (e.g. cp-api 4xx). */
  errorMessage?: string;
}

const STATUS_LABEL: Record<SsoStatus, string> = {
  not_connected: "Not connected",
  pending: "Pending ACS round-trip",
  connected: "Connected",
  error: "Error",
};

export function EnterpriseSsoForm({ status, onSubmit, errorMessage }: EnterpriseSsoFormProps) {
  const [metadataUrl, setMetadataUrl] = useState("");
  const [metadataXml, setMetadataXml] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleFile(file: File | null) {
    if (!file) {
      setMetadataXml("");
      return;
    }
    // Use FileReader rather than File.text() — older jsdom builds (and a
    // handful of older browsers) ship File without the .text() Promise
    // method, so the reader is the safest cross-environment path.
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      setMetadataXml(typeof result === "string" ? result : "");
    };
    reader.readAsText(file);
  }

  return (
    <form
      data-testid="enterprise-sso-form"
      className="flex max-w-xl flex-col gap-4"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!metadataUrl && !metadataXml) {
          setLocalError("Provide either a metadata URL or upload metadata XML.");
          return;
        }
        if (metadataUrl && metadataXml) {
          setLocalError("Provide one of metadata URL or XML, not both.");
          return;
        }
        setLocalError(null);
        setSubmitting(true);
        try {
          await onSubmit(
            metadataUrl ? { metadataUrl } : { metadataXml },
          );
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Status:</span>
        <span
          data-testid="enterprise-sso-status"
          data-status={status}
          className="rounded-full border px-2 py-0.5 text-xs"
        >
          {STATUS_LABEL[status]}
        </span>
      </div>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">IdP metadata URL</span>
        <input
          type="url"
          data-testid="enterprise-sso-metadata-url"
          className="rounded-md border bg-background px-2 py-1"
          value={metadataUrl}
          placeholder="https://login.example.com/app/.../sso/saml/metadata"
          onChange={(e) => setMetadataUrl(e.target.value)}
        />
      </label>

      <div className="text-center text-xs uppercase text-muted-foreground">or</div>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Upload IdP metadata XML</span>
        <input
          type="file"
          accept=".xml,application/xml,text/xml"
          data-testid="enterprise-sso-metadata-file"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
        {metadataXml && (
          <span
            data-testid="enterprise-sso-xml-loaded"
            className="text-xs text-muted-foreground"
          >
            Loaded {metadataXml.length} bytes of metadata.
          </span>
        )}
      </label>

      <p
        data-testid="enterprise-sso-help"
        className="text-xs text-muted-foreground"
        role="note"
      >
        Status flips to <strong>Connected</strong> only after a successful ACS
        round-trip from your IdP. If it stays <strong>Pending</strong>, verify the ACS URL and
        Entity ID configured at the IdP match the values shown in your workspace.
      </p>

      {(localError || errorMessage) && (
        <p
          data-testid="enterprise-sso-error"
          className="text-sm text-red-600"
          role="alert"
        >
          {localError ?? errorMessage}
        </p>
      )}

      <button
        type="submit"
        data-testid="enterprise-sso-submit"
        disabled={submitting}
        className="rounded-md border bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
      >
        {submitting ? "Connecting…" : "Connect IdP"}
      </button>
    </form>
  );
}
