import { SectionDegraded } from "@/components/section-states";
import { VoiceDemoLanding } from "@/components/voice/voice-demo-landing";
import { fetchVoiceDemoLink } from "@/lib/voice-demo";

export const dynamic = "force-dynamic";

export default async function VoiceDemoPage({
  params,
}: {
  params: { token: string };
}): Promise<JSX.Element> {
  const demo = await fetchVoiceDemoLink(params.token).catch((error: unknown) => {
    const message =
      error instanceof Error ? error.message : "Voice demo link could not be loaded.";
    return { degradedReason: message };
  });

  if ("degradedReason" in demo) {
    return (
      <main className="mx-auto w-full max-w-4xl p-6" data-testid="voice-demo-page">
        <SectionDegraded
          title="Voice demo link"
          description="Studio could not verify this voice demo link. It will not open an unaudited or expired voice session."
          evidence={demo.degradedReason}
        />
      </main>
    );
  }

  return <VoiceDemoLanding demo={demo} token={params.token} />;
}
