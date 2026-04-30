import { InboxScreen } from "@/components/inbox/inbox-screen";
import {
  FIXTURE_INBOX,
  FIXTURE_NOW_MS,
  FIXTURE_OPERATOR_ID,
  FIXTURE_WORKSPACE_ID,
} from "@/lib/inbox";

export const dynamic = "force-dynamic";

export default function InboxPage(): JSX.Element {
  return (
    <InboxScreen
      initialItems={FIXTURE_INBOX}
      workspace_id={FIXTURE_WORKSPACE_ID}
      operator_id={FIXTURE_OPERATOR_ID}
      now_ms={FIXTURE_NOW_MS}
    />
  );
}
