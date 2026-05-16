import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Compass,
  FileText,
  Gauge,
  GitBranch,
  LockKeyhole,
  MessagesSquare,
  Radar,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { AgentGlassOrb } from "@/components/agents/agent-glass-orb";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const proofPoints = [
  {
    label: "Governed from day one",
    detail:
      "Every agent starts with an owner, a scope, and the proofs it needs to ship.",
    icon: FileText,
  },
  {
    label: "Talks where your people are",
    detail:
      "Web, WhatsApp, Slack, voice, email, and the rest — one agent, every channel.",
    icon: MessagesSquare,
  },
  {
    label: "Proof in production",
    detail:
      "Traces, tests, approvals, costs, and incidents stay attached to every release.",
    icon: Radar,
  },
  {
    label: "Enterprise from the start",
    detail:
      "SSO, roles, audit, region pinning, and admin review come built in.",
    icon: ShieldCheck,
  },
];

const channelOrbits = [
  { label: "Web", style: "left-[10%] top-[14%]" },
  { label: "Slack", style: "right-[6%] top-[10%]" },
  { label: "WhatsApp", style: "left-[2%] top-[56%]" },
  { label: "Voice", style: "right-[2%] top-[58%]" },
  { label: "Webhook", style: "left-[44%] top-[88%]" },
] as const;

const launchSteps = [
  {
    n: "01",
    title: "Create your workspace",
    detail: "Workspace, region, SSO, and your first admin — set up in minutes.",
  },
  {
    n: "02",
    title: "Bring in the team",
    detail: "Invite admins, builders, reviewers, and operators with scoped roles.",
  },
  {
    n: "03",
    title: "Build or migrate",
    detail: "Define what an agent should do, or bring over what you already have.",
  },
  {
    n: "04",
    title: "Ship with proof",
    detail: "Replays, tests, approvals, canary, and rollback for every release.",
  },
] as const;

function HeroOrb() {
  return (
    <div className="relative mx-auto flex h-[26rem] w-[26rem] items-center justify-center sm:h-[30rem] sm:w-[30rem]">
      {channelOrbits.map(({ label, style }) => (
        <span
          key={label}
          className={cn(
            "floating-glass-badge absolute inline-flex items-center rounded-full px-3 py-1 text-[0.7rem] font-medium tracking-wide text-muted-foreground",
            style,
          )}
        >
          {label}
        </span>
      ))}
      <AgentGlassOrb
        agentId="loop_studio_hero"
        label="Loop hero agent"
        size="hero"
        decorative
        quiet
      />
    </div>
  );
}

export function WelcomeLanding() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 pt-6 sm:px-8 lg:px-12">
        <Link
          href="/"
          className="glass-pill inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-semibold tracking-tight"
        >
          Loop Studio
        </Link>
        <nav className="glass-pill hidden items-center gap-1 rounded-full px-1 py-1 text-sm md:flex">
          {[
            { href: "/welcome", label: "Product" },
            { href: "/welcome", label: "Governance" },
            { href: "/welcome", label: "Pricing" },
            { href: "/welcome", label: "Docs" },
          ].map(({ href, label }) => (
            <Link
              key={label}
              href={href}
              className="rounded-full px-3 py-1.5 text-muted-foreground hover:text-foreground"
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link
            href="/login"
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className={cn(
              buttonVariants({ variant: "default", size: "sm" }),
              "shadow-[0_18px_42px_-18px_hsl(var(--primary)/0.6)]",
            )}
          >
            Get started
          </Link>
        </div>
      </header>

      <section className="relative z-10 mx-auto grid w-full max-w-7xl gap-12 px-5 pt-16 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-center lg:px-12 lg:pt-24">
        <div className="max-w-xl">
          <span className="glass-pill inline-flex items-center gap-2 rounded-full px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            <Sparkles className="h-3 w-3 text-primary" aria-hidden />
            Glass-box control plane
          </span>
          <h1 className="mt-7 text-5xl font-semibold leading-[0.96] tracking-tight sm:text-6xl lg:text-[4.5rem]">
            <span className="text-pearl">Agents you can</span>
            <br />
            <span className="text-pearl">see through.</span>
          </h1>
          <p className="mt-7 max-w-md text-lg leading-[1.65] text-muted-foreground">
            The control room for production agents. Define what they
            should do, connect them to your channels, and ship every
            release with proof your audit team can sign.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/signup"
              className={cn(
                buttonVariants({ size: "lg" }),
                "shadow-[0_24px_60px_-22px_hsl(var(--primary)/0.7)]",
              )}
            >
              Get started
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
            </Link>
            <Link
              href="/login?returnTo=/home"
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              Open Studio
            </Link>
          </div>
          <div className="mt-10 grid grid-cols-2 gap-3 text-xs sm:max-w-md sm:grid-cols-4">
            {[
              "Import from Botpress",
              "SSO and roles",
              "Replay a real conversation",
              "Turn handoffs into tests",
            ].map((label) => (
              <span
                key={label}
                className="inline-flex items-center gap-1.5 text-muted-foreground"
              >
                <CheckCircle2 className="h-3 w-3 text-primary" aria-hidden />
                {label}
              </span>
            ))}
          </div>
        </div>

        <div className="relative">
          <HeroOrb />
        </div>
      </section>

      <div className="relative z-10 mx-auto mt-24 h-px max-w-5xl px-5 sm:px-8 lg:px-12">
        <div className="prism-seam h-px w-full opacity-50" aria-hidden />
      </div>

      <section className="relative z-10 mx-auto mt-20 max-w-7xl px-5 sm:px-8 lg:px-12">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.42fr)_minmax(0,0.58fr)] lg:items-start">
          <div>
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              How you get there
            </p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
              From sign-up to live agents in four steps.
            </h2>
            <p className="mt-4 max-w-md text-sm leading-7 text-muted-foreground">
              Every change is owned, reviewed, and reversible before it
              reaches customers.
            </p>
          </div>
          <ol className="grid gap-2.5">
            {launchSteps.map(({ n, title, detail }) => (
              <li
                key={n}
                className="instrument-panel interactive-lift flex items-start gap-4 rounded-2xl p-5"
              >
                <span className="font-mono text-xs font-semibold tabular-nums text-primary/70">
                  {n}
                </span>
                <div>
                  <p className="font-semibold text-foreground">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    {detail}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="relative z-10 mx-auto mt-24 max-w-7xl px-5 pb-12 sm:px-8 lg:px-12">
        <div className="mb-10 max-w-2xl">
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            What you ship with
          </p>
          <h3 className="mt-3 text-3xl font-semibold leading-tight tracking-tight">
            Four proof marks come standard.
          </h3>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {proofPoints.map(({ label, detail, icon: Icon }) => (
            <article
              key={label}
              className="instrument-panel interactive-lift rounded-2xl p-6"
            >
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <h2 className="mt-5 text-base font-semibold">{label}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {detail}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto mb-20 max-w-7xl px-5 sm:px-8 lg:px-12">
        <div className="glass-deep relative flex flex-col items-start gap-6 overflow-hidden rounded-3xl p-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative max-w-xl">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Ready when you are
            </p>
            <p className="mt-3 text-2xl font-semibold leading-tight tracking-tight">
              Bring your team into the same glass box.
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Invite owners, builders, reviewers, and operators with scoped
              roles. Region, SSO, and audit are configured before you ship.
            </p>
          </div>
          <div className="relative flex flex-col items-stretch gap-2 sm:items-end">
            <Link
              href="/signup"
              className={cn(
                buttonVariants({ size: "lg" }),
                "shadow-[0_24px_60px_-22px_hsl(var(--primary)/0.7)]",
              )}
            >
              Create your workspace
            </Link>
            <Link
              href="/login"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Have an invite? Sign in →
            </Link>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Compass className="h-3 w-3" aria-hidden />
            <span>Region pinning · BYOK · audit forwarding · SCIM</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 tabular-nums">
              <GitBranch className="h-3 w-3" aria-hidden />
              v23.1.4
            </span>
            <span className="flex items-center gap-1.5 tabular-nums">
              <Gauge className="h-3 w-3" aria-hidden />
              842ms p95
            </span>
            <span className="flex items-center gap-1.5">
              <LockKeyhole className="h-3 w-3" aria-hidden />
              SAML enforced
            </span>
          </div>
        </div>
      </section>
    </main>
  );
}
