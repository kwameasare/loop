import { EyeOff, ShieldCheck } from "lucide-react";

import { SectionDegraded } from "@/components/section-states";
import { LiveBadge } from "@/components/target";
import { fetchPublicShare } from "@/lib/sharing";

export const dynamic = "force-dynamic";

export default async function PublicSharePage({
  params,
}: {
  params: { token: string };
}): Promise<JSX.Element> {
  const share = await fetchPublicShare(params.token).catch((error: unknown) => {
    const message =
      error instanceof Error ? error.message : "Share link could not be loaded.";
    return { degradedReason: message };
  });

  if ("degradedReason" in share) {
    return (
      <main className="mx-auto w-full max-w-4xl p-6" data-testid="share-page">
        <SectionDegraded
          title="Share link"
          description="Studio could not verify this share link. It will not render unaudited or expired shared evidence."
          evidence={share.degradedReason}
        />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-5 p-6" data-testid="share-page">
      <header className="instrument-panel rounded-2xl p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">
              Shared evidence
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {share.source_type} · {share.source_id}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              This public view is server-redacted and every open is written to
              the workspace audit log.
            </p>
          </div>
          <LiveBadge tone="live">audited</LiveBadge>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <article className="instrument-panel rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <EyeOff className="h-5 w-5 text-info" aria-hidden={true} />
            <div>
              <h2 className="text-sm font-semibold">Recipient redaction view</h2>
              <p className="text-xs text-muted-foreground">
                {share.redaction_banner}
              </p>
            </div>
          </div>
          <ul className="mt-4 flex flex-wrap gap-2">
            {share.redactions.length > 0 ? (
              share.redactions.map((category) => (
                <li
                  key={category}
                  className="rounded-md border bg-background px-2 py-1 text-xs"
                >
                  {category}
                </li>
              ))
            ) : (
              <li className="text-xs text-muted-foreground">
                No redaction categories were requested.
              </li>
            )}
          </ul>
        </article>

        <article className="instrument-panel rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-success" aria-hidden={true} />
            <div>
              <h2 className="text-sm font-semibold">Expiry and audit</h2>
              <p className="text-xs text-muted-foreground">
                Expires {new Date(share.expires_at).toLocaleString()}
              </p>
            </div>
          </div>
          <p className="mt-4 font-mono text-xs text-muted-foreground">
            share id: {share.id}
          </p>
        </article>
      </section>
    </main>
  );
}
