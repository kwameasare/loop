"use client";

import { SectionError } from "@/components/section-states";

export default function InboxError({ reset }: { reset: () => void }) {
  return <SectionError title="Inbox" reset={reset} />;
}
