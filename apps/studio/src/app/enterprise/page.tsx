import { IdpConnectPanel } from "@/components/enterprise/idp-connect-panel";
import {
  FIXTURE_IDP_NOT_CONFIGURED,
  postIdpMetadata,
  type IdpMetadataSource,
} from "@/lib/enterprise";

export const dynamic = "force-dynamic";

/**
 * Fixture submit action — used by the dev server and screenshot tests.
 *
 * In production this would call postIdpMetadata with a server-side
 * token; the panel's `onConnect` prop keeps the real call out of the
 * component so the component stays testable.
 */
async function fixtureConnect(source: IdpMetadataSource) {
  "use server";
  // In the dev fixture we return the pending state without hitting the
  // real API.  A production page would pass a real token here.
  void source;
  return {
    status: "pending_verification" as const,
    entity_id: "https://dev.okta.com/app/fixture/entity",
    acs_url: "https://app.loop.dev/auth/saml/acs/ws-fixture",
    connected_at: null,
  };
}

export default function EnterprisePage(): JSX.Element {
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
      <IdpConnectPanel
        connection={FIXTURE_IDP_NOT_CONFIGURED}
        onConnect={fixtureConnect}
      />
    </main>
  );
}
