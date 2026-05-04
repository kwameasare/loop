import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

/**
 * Studio home placeholder. Real surfaces (workspace switcher, agent list,
 * conversation explorer) land in stories S025–S036 (epic E10). Until then
 * the home page links into the existing section pages so reviewers can
 * walk the studio without typing routes by hand.
 */
export default function HomePage() {
  return (
    <main className="container mx-auto flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-6 px-4">
      <h1 className="text-4xl font-semibold tracking-tight">Loop Studio</h1>
      <p className="text-muted-foreground max-w-xl text-center">
        The agent-first control plane. This skeleton ships the design-token
        bus, App Router shell, and the shadcn primitives so feature stories
        can ship UI without re-doing plumbing. Pick a section from the nav
        above or jump straight in.
      </p>
      <div className="flex gap-3">
        <Link href="/agents" className={buttonVariants()}>
          Get started
        </Link>
        <Link
          href="/inbox"
          className={buttonVariants({ variant: "outline" })}
        >
          View inbox
        </Link>
      </div>
    </main>
  );
}
