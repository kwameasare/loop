import { Button } from "@/components/ui/button";

/**
 * Studio home placeholder. Real surfaces (workspace switcher, agent list,
 * conversation explorer) land in stories S025–S036 (epic E10).
 */
export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6">
      <h1 className="text-4xl font-semibold tracking-tight">Loop Studio</h1>
      <p className="text-muted-foreground max-w-xl text-center">
        The agent-first control plane. This skeleton ships the design-token
        bus, App Router shell, and the shadcn primitives so feature stories
        can ship UI without re-doing plumbing.
      </p>
      <div className="flex gap-3">
        <Button>Get started</Button>
        <Button variant="outline">View docs</Button>
      </div>
    </main>
  );
}
