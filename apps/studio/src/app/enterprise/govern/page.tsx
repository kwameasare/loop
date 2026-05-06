"use client";

import { GovernOverview } from "@/components/enterprise/govern-overview";

export default function EnterpriseGovernPage(): JSX.Element {
  return (
    <main
      data-testid="enterprise-govern-page"
      className="mx-auto max-w-6xl p-6"
    >
      <GovernOverview />
    </main>
  );
}
