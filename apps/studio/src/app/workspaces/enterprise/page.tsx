"use client";

/**
 * P0.3: ``/workspaces/enterprise`` — workspace-scoped SAML config.
 *
 * Replaces the previous ``console.info("[sso] would POST", ...)``
 * stub with a real cp-api round-trip via ``postSamlConfig``. Until
 * the cp shim ships the call 404s and the form surfaces the
 * "blocked on cp-api PR" error so customers don't think it's
 * silently working.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import {
  EnterpriseSsoForm,
  type EnterpriseSsoSubmitPayload,
  type SsoStatus,
} from "@/components/workspaces/enterprise-sso-form";
import {
  fetchSamlConfig,
  postSamlConfig,
  type SamlConfigResponse,
} from "@/lib/enterprise";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

function toSsoStatus(s: SamlConfigResponse["status"]): SsoStatus {
  if (s === "connected") return "connected";
  if (s === "pending_verification") return "pending";
  return "not_connected";
}

export default function EnterpriseSsoPage() {
  return (
    <RequireAuth>
      <EnterpriseSsoBody />
    </RequireAuth>
  );
}

function EnterpriseSsoBody() {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [status, setStatus] = useState<SsoStatus>("not_connected");
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void fetchSamlConfig(active.id)
      .then((c) => {
        if (cancelled) return;
        setStatus(toSsoStatus(c.status));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Could not load SSO config",
        );
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  async function handleSubmit(payload: EnterpriseSsoSubmitPayload) {
    if (!active) return;
    setErrorMessage(undefined);
    setStatus("pending");
    try {
      const next = await postSamlConfig(active.id, {
        ...(payload.metadataUrl ? { metadata_url: payload.metadataUrl } : {}),
        ...(payload.metadataXml ? { metadata_xml: payload.metadataXml } : {}),
      });
      setStatus(toSsoStatus(next.status));
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to connect IdP.",
      );
      setStatus("error");
    }
  }

  if (wsLoading || !active) {
    return (
      <main className="flex flex-col gap-4 p-6">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    );
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
        {...(errorMessage ? { errorMessage } : {})}
      />
    </main>
  );
}
