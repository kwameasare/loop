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
import { WorkspaceRequiredState } from "@/components/section-states";
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
  const activeWorkspaceId = active?.id;
  const [status, setStatus] = useState<SsoStatus>("not_connected");
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined,
  );
  const [backendUnavailable, setBackendUnavailable] = useState(false);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void fetchSamlConfig(activeWorkspaceId)
      .then((c) => {
        if (cancelled) return;
        if (c.degraded_reason) {
          setErrorMessage(c.degraded_reason);
          setBackendUnavailable(true);
          setStatus("error");
          return;
        }
        setBackendUnavailable(false);
        setErrorMessage(undefined);
        setStatus(toSsoStatus(c.status));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Could not load SSO config",
        );
        setBackendUnavailable(true);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  async function handleSubmit(payload: EnterpriseSsoSubmitPayload) {
    if (!activeWorkspaceId) return;
    setErrorMessage(undefined);
    setBackendUnavailable(false);
    setStatus("pending");
    try {
      const next = await postSamlConfig(activeWorkspaceId, {
        ...(payload.metadataUrl ? { metadata_url: payload.metadataUrl } : {}),
        ...(payload.metadataXml ? { metadata_xml: payload.metadataXml } : {}),
      });
      setStatus(toSsoStatus(next.status));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to connect IdP.";
      setErrorMessage(message);
      setBackendUnavailable(
        /404|route not yet shipped|LOOP_CP_API_BASE_URL/i.test(message),
      );
      setStatus("error");
    }
  }

  if (wsLoading) {
    return (
      <main className="flex flex-col gap-4 p-6">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    );
  }
  if (!activeWorkspaceId) {
    return <WorkspaceRequiredState title="Enterprise SSO" />;
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
        {...(backendUnavailable ? { disabled: true } : {})}
      />
    </main>
  );
}
