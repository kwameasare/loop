import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type HomepagePinSourceType =
  | "dashboard"
  | "observatory_metric"
  | "trace"
  | "eval_case"
  | "eval_suite"
  | "audit_filter"
  | "agent"
  | "incident"
  | string;

export interface HomepagePin {
  id: string;
  source_type: HomepagePinSourceType;
  source_id: string;
  title: string;
  href: string;
  created_at: string;
}

export interface HomepagePinsResponse {
  items: HomepagePin[];
  degradedReason?: string | undefined;
}

export interface CreateHomepagePinInput {
  source_type: HomepagePinSourceType;
  source_id: string;
  title: string;
  href: string;
}

export interface HomepagePinsClientOptions extends UxWireupClientOptions {
  allowFixture?: boolean;
}

const EMPTY_PINS: HomepagePin[] = [];

function normalisePins(items: readonly HomepagePin[] | undefined): HomepagePin[] {
  return [...(items ?? [])].filter(
    (item) => item.title.trim() && item.href.trim(),
  );
}

export async function fetchHomepagePins(
  workspaceId: string | null | undefined,
  opts: HomepagePinsClientOptions = {},
): Promise<HomepagePinsResponse> {
  if (!workspaceId) {
    return {
      items: EMPTY_PINS,
      degradedReason: "No active workspace id is available for homepage pins.",
    };
  }

  try {
    const body = await cpJson<{ items: HomepagePin[] }>(
      `/workspaces/${encodeURIComponent(workspaceId)}/homepage/pins`,
      {
        ...opts,
        fallback: { items: EMPTY_PINS },
        allowFallback: opts.allowFixture === true,
      },
    );
    return { items: normalisePins(body.items) };
  } catch (error) {
    return {
      items: EMPTY_PINS,
      degradedReason:
        error instanceof Error
          ? `Homepage pins unavailable: ${error.message}`
          : "Homepage pins unavailable.",
    };
  }
}

export async function createHomepagePin(
  workspaceId: string,
  input: CreateHomepagePinInput,
  opts: HomepagePinsClientOptions = {},
): Promise<HomepagePin> {
  return cpJson<HomepagePin>(
    `/workspaces/${encodeURIComponent(workspaceId)}/homepage/pins`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        id: `pin_local_${input.source_type}_${input.source_id}`,
        ...input,
        created_at: new Date(0).toISOString(),
      },
      allowFallback: opts.allowFixture === true,
    },
  );
}
