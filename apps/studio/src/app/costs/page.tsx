import { CostPageClient } from "@/components/cost/cost-page-client";
import {
  FIXTURE_NOW_MS,
  FIXTURE_USAGE,
  FIXTURE_WORKSPACE_ID,
} from "@/lib/costs";

export const dynamic = "force-dynamic";

export default function CostsPage(): JSX.Element {
  return (
    <CostPageClient
      records={FIXTURE_USAGE}
      workspace_id={FIXTURE_WORKSPACE_ID}
      now_ms={FIXTURE_NOW_MS}
    />
  );
}
