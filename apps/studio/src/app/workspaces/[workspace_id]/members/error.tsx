"use client";

import { Button } from "@/components/ui/button";

export default function MembersError({ reset }: { reset: () => void }) {
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <div className="rounded-lg border p-4" role="alert">
        <h2 className="text-base font-medium">Members could not load</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          The cp-api request failed. Retry or sign back in if the session
          expired.
        </p>
        <Button className="mt-4" onClick={reset} variant="outline">
          Retry
        </Button>
      </div>
    </main>
  );
}
