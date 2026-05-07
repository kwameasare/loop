import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface TelemetryConsentModel {
  workspace_id: string;
  user_sub: string;
  product_analytics: boolean | null;
  diagnostics: boolean | null;
  ai_improvement: boolean | null;
  crash_reports: boolean | null;
  annual_review_due: boolean;
  admin_overrides?: Record<string, boolean>;
}

export interface HelpClip {
  clip_id: string;
  surface: string;
  url: string;
  duration: number;
  transcript: string;
}

export async function fetchTelemetryConsent(
  workspaceId: string,
  opts: UxWireupClientOptions = {},
): Promise<TelemetryConsentModel> {
  return cpJson<TelemetryConsentModel>(
    `/workspaces/${encodeURIComponent(workspaceId)}/telemetry-consent`,
    {
      ...opts,
      fallback: {
        workspace_id: workspaceId,
        user_sub: "local-builder",
        product_analytics: null,
        diagnostics: null,
        ai_improvement: null,
        crash_reports: null,
        annual_review_due: true,
      },
    },
  );
}

export async function saveTelemetryConsent(
  workspaceId: string,
  consent: {
    product_analytics: boolean;
    diagnostics: boolean;
    ai_improvement: boolean;
    crash_reports: boolean;
  },
  opts: UxWireupClientOptions = {},
): Promise<TelemetryConsentModel> {
  return cpJson<TelemetryConsentModel>(
    `/workspaces/${encodeURIComponent(workspaceId)}/telemetry-consent`,
    {
      ...opts,
      method: "POST",
      body: consent,
      fallback: {
        workspace_id: workspaceId,
        user_sub: "local-builder",
        ...consent,
        annual_review_due: false,
      },
    },
  );
}

export async function fetchHelpClips(
  surface: string,
  opts: UxWireupClientOptions = {},
): Promise<HelpClip[]> {
  const suffix = surface ? `?surface=${encodeURIComponent(surface)}` : "";
  const body = await cpJson<{ items: HelpClip[] }>(`/help-clips${suffix}`, {
    ...opts,
    fallback: {
      items: [
        {
          clip_id: "clip_local_show_me",
          surface: surface || "current",
          url: "/help/clips/local-show-me.mp4",
          duration: 30,
          transcript: "Show me the safest next step on this surface.",
        },
      ],
    },
  });
  return body.items;
}
