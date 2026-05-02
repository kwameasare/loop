"use client";

/**
 * S615: Enterprise SSO settings page.
 *
 * Hosts the ``EnterpriseSsoForm`` and is responsible for the cp-api
 * round-trip. The form is intentionally pure UI; the page owns the
 * client and the polling loop that flips the status to
 * ``connected`` after a successful ACS round-trip.
 *
 * cp-api SSO endpoints land in S617; until then this page renders
 * the form with a stub submit handler that surfaces the request
 * payload so the user can preview what would be POSTed. Once the
 * generated client lands the stub is dropped without a UI change.
 */

import { useState } from "react";

import {
  EnterpriseSsoForm,
  type EnterpriseSsoSubmitPayload,
  type SsoStatus,
} from "@/components/workspaces/enterprise-sso-form";

export default function EnterpriseSsoPage() {
  const [status, setStatus] = useState<SsoStatus>("not_connected");
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);

  async function handleSubmit(payload: EnterpriseSsoSubmitPayload) {
    setErrorMessage(undefined);
    setStatus("pending");
    try {
      // Stubbed cp-api call. S617 swaps this for a generated client
      // call to ``POST /v1/workspaces/{id}/sso``. The pending → connected
      // transition is driven by an ACS round-trip from the IdP, so the
      // status will remain ``pending`` here until the auth callback
      // route posts back via a server-sent event or a polled GET.
      console.info("[sso] would POST", payload);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to connect IdP.");
      setStatus("error");
    }
  }

  return (
    <main className="flex flex-col gap-4 p-6">
      <h1 className="text-xl font-semibold">Enterprise SSO</h1>
      <p className="max-w-xl text-sm text-muted-foreground">
        Connect your SAML 2.0 identity provider (Okta, Microsoft Entra ID, or
        Google Workspace) to enable single sign-on for this workspace. Members
        will continue to use their existing IdP credentials.
      </p>
      <EnterpriseSsoForm
        status={status}
        onSubmit={handleSubmit}
        errorMessage={errorMessage}
      />
    </main>
  );
}
