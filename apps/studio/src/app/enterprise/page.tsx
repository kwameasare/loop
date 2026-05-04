"use client";

/**
 * P0.3: ``/enterprise`` — workspace SAML setup.
 *
 * Wires the IdpConnectPanel to ``GET/POST /v1/workspaces/{id}/enterprise/saml``.
 * The cp-api shim isn't mounted yet (see lib/enterprise.ts
 * fetchSamlConfig); on 404 the panel renders an explicit
 * ``not_configured`` state — no more hardcoded ACS URL fixture.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { IdpConnectPanel } from "@/components/enterprise/idp-connect-panel";
import {
  fetchSamlConfig,
  postSamlConfig,
  type IdpMetadataSource,
  type SamlConfigResponse,
} from "@/lib/enterprise";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function EnterprisePage(): JSX.Element {
  return (
    <RequireAuth>
      <EnterprisePageBody />
    </RequireAuth>
  );
}

function EnterprisePageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [config, setConfig] = useState<SamlConfigResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void fetchSamlConfig(active.id)
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load SAML config");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  async function handleConnect(source: IdpMetadataSource) {
    if (!active) {
      throw new Error("No active workspace");
    }
    const body =
      "url" in source
        ? { metadata_url: source.url }
        : { metadata_xml: source.xml };
    const next = await postSamlConfig(active.id, body);
    setConfig(next);
    return {
      status: next.status,
      entity_id: next.entity_id,
      acs_url: next.acs_url,
      connected_at: next.connected_at,
    };
  }

  if (wsLoading || !active || (!config && !error)) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground" data-testid="enterprise-loading">
          Loading SAML configuration…
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </main>
    );
  }
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Enterprise</h1>
        <p className="text-muted-foreground text-sm">
          Connect a SAML 2.0 Identity Provider so your team can sign in with
          SSO. Paste the IdP metadata URL or upload the raw XML. After
          uploading, complete a test login to verify the ACS round-trip and
          move the status to Connected.
        </p>
      </header>
      <IdpConnectPanel connection={config!} onConnect={handleConnect} />
    </main>
  );
}
