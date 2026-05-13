import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Building2,
  CheckCircle2,
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
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const proofPoints = [
  {
    label: "Governed from intake",
    detail:
      "Every agent begins as a commitment with owner, channels, limits, and proof gates.",
    icon: FileText,
  },
  {
    label: "Omnichannel by design",
    detail:
      "Web, WhatsApp, Telegram, Slack, Teams, SMS, email, voice, and webhooks are peer bindings.",
    icon: MessagesSquare,
  },
  {
    label: "Production evidence",
    detail:
      "Traces, evals, approvals, costs, and incidents stay linked to each release.",
    icon: Radar,
  },
  {
    label: "Enterprise control",
    detail:
      "SSO, invitations, roles, audit, residency, and system-admin review are first-class.",
    icon: ShieldCheck,
  },
];

const sceneRows = [
  ["Intake contract", "Owner set", "Channels selected", "Evidence required"],
  [
    "Replay against draft",
    "Eval gate green",
    "Approval hash bound",
    "Canary ready",
  ],
  [
    "Trace scrubber",
    "HITL saved as eval",
    "Rollback prepared",
    "Audit exported",
  ],
] as const;

const sceneMetrics = [
  { label: "Trace", value: "t_9b23", icon: Radar },
  { label: "Version", value: "v23.1.4", icon: GitBranch },
  { label: "Latency", value: "842ms", icon: Gauge },
  { label: "Access", value: "SAML enforced", icon: LockKeyhole },
] as const;

const channelBadges = [
  ["Web", "left-[10%] top-[31%]"],
  ["WhatsApp", "left-[22%] top-[58%]"],
  ["Slack", "left-[30%] top-[20%]"],
  ["Telegram", "right-[21%] top-[24%]"],
  ["SMS", "right-[10%] top-[45%]"],
  ["Voice", "right-[23%] top-[64%]"],
] as const;

function HeroScene() {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden="true"
    >
      <div className="absolute inset-4 rounded-[2rem] border border-border/55 bg-card/34 shadow-[0_30px_90px_hsl(var(--glass-shadow)/0.18)] backdrop-blur-2xl sm:inset-8" />
      <div className="orbital-lattice absolute inset-4 rounded-[2rem] sm:inset-8" />
      <div className="absolute inset-4 rounded-[2rem] bg-[linear-gradient(115deg,hsl(var(--background)/0.88),hsl(var(--surface)/0.58)_48%,hsl(var(--background)/0.82)),linear-gradient(40deg,hsl(var(--aurora-a)/0.16),transparent_42%,hsl(var(--aurora-c)/0.14))] sm:inset-8" />
      {channelBadges.map(([label, position], index) => (
        <div
          key={label}
          className={cn(
            "floating-glass-badge absolute hidden items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold 2xl:flex",
            position,
          )}
        >
          <AgentGlassOrb agentId={label} label={label} size="sm" />
          <span>{label}</span>
          <span className="text-muted-foreground tabular-nums">
            {index + 1}
          </span>
        </div>
      ))}
      <div className="floating-glass-badge absolute left-[6%] top-[18%] hidden w-80 rotate-[-3deg] rounded-2xl p-4 2xl:block">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase text-muted-foreground">
            Estate health
          </span>
          <span className="rounded-full bg-primary/15 px-2 py-1 text-xs font-medium text-primary">
            measured
          </span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {["96", "4", "0"].map((value, index) => (
            <div key={value} className="rounded-xl border bg-background/62 p-3">
              <p className="text-xl font-semibold">{value}</p>
              <p className="mt-1 text-[0.65rem] uppercase text-muted-foreground">
                {["health", "agents", "blocked"][index]}
              </p>
            </div>
          ))}
        </div>
      </div>
      <div className="floating-glass-badge absolute right-[5%] top-[14%] hidden w-[26rem] rotate-[2deg] rounded-2xl p-4 2xl:block">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Bot className="h-4 w-4 text-primary" />
          Agent release package
        </div>
        <div className="mt-4 space-y-2">
          {sceneRows.map((row, rowIndex) => (
            <div key={row.join("-")} className="grid grid-cols-4 gap-2">
              {row.map((item, index) => (
                <span
                  key={item}
                  className={cn(
                    "rounded-xl border px-2 py-1.5 text-[0.68rem] font-medium text-muted-foreground",
                    rowIndex === 1 && index === 2
                      ? "border-primary/50 bg-primary/12 text-primary"
                      : "bg-background/72",
                  )}
                >
                  {item}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="floating-glass-badge absolute bottom-[8%] left-1/2 hidden w-[44rem] -translate-x-1/2 rounded-2xl p-3 2xl:block">
        <div className="grid grid-cols-4 gap-2 text-xs">
          {sceneMetrics.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-xl bg-background/72 p-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Icon className="h-3.5 w-3.5" />
                <span>{label}</span>
              </div>
              <p className="mt-2 font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function WelcomeLanding() {
  return (
    <main className="min-h-screen overflow-hidden">
      <section className="relative flex min-h-[92vh] items-center px-5 py-8 sm:px-8 lg:px-12">
        <HeroScene />
        <div className="relative z-10 mx-auto grid w-full max-w-7xl gap-10 pt-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(28rem,0.8fr)] lg:items-center">
          <div className="max-w-3xl">
            <nav className="floating-glass-badge mb-12 flex items-center justify-between gap-4 rounded-full px-3 py-2 text-sm">
              <Link
                href="/"
                className="inline-flex items-center gap-2 font-semibold"
              >
                <AgentGlassOrb label="Loop Studio" size="md" decorative />
                <span>Loop Studio</span>
              </Link>
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className={buttonVariants({ variant: "ghost", size: "sm" })}
                >
                  Sign in
                </Link>
                <Link
                  href="/signup"
                  className={buttonVariants({ variant: "default", size: "sm" })}
                >
                  Get started
                </Link>
              </div>
            </nav>

            <h1 className="max-w-4xl text-5xl font-semibold leading-[0.96] text-foreground sm:text-6xl lg:text-7xl">
              Loop Studio
            </h1>
            <p className="mt-6 max-w-2xl text-xl leading-8 text-muted-foreground">
              Build agents with light around every decision. This is the
              glass-box control plane for creating, governing, testing,
              deploying, and operating AI agents across every customer channel.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/signup" className={buttonVariants({ size: "lg" })}>
                Start enterprise signup
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
              </Link>
              <Link
                href="/login?returnTo=/home"
                className={buttonVariants({ variant: "outline", size: "lg" })}
              >
                Open Studio
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-3 text-sm text-muted-foreground">
              {[
                "Botpress import",
                "SSO and roles",
                "Trace replay",
                "HITL to eval",
              ].map((item) => (
                <span
                  key={item}
                  className="floating-glass-badge inline-flex items-center gap-1.5 rounded-full px-3 py-1"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="relative hidden lg:block">
            <div className="instrument-panel breathing-well relative rounded-2xl p-5">
              <AgentGlassOrb
                agentId="enterprise-launch-agent"
                label="Enterprise launch agent"
                size="xl"
                state="watching"
                className="absolute -right-3 -top-3 opacity-90"
              />
              <div className="flex items-center justify-between gap-3">
                <div className="max-w-[72%]">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Enterprise launch path
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold">
                    From signup to governed agent estate
                  </h2>
                </div>
                <Sparkles className="h-5 w-5 text-primary" aria-hidden />
              </div>
              <div className="mt-5 space-y-3">
                {[
                  [
                    "1",
                    "Create enterprise tenant",
                    "Workspace, region, SSO intent, admin invite.",
                  ],
                  [
                    "2",
                    "Onboard builders",
                    "Owners invite admins, builders, reviewers, and operators.",
                  ],
                  [
                    "3",
                    "Create or import agents",
                    "Commitment document first; channels are bound explicitly.",
                  ],
                  [
                    "4",
                    "Ship with proof",
                    "Replay, eval gates, approvals, canary, rollback evidence.",
                  ],
                ].map(([step, title, detail]) => (
                  <div
                    key={step}
                    className="interactive-lift rounded-md border bg-background/72 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
                        {step}
                      </span>
                      <div>
                        <p className="font-semibold">{title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {detail}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 border-t bg-background/82 px-5 py-12 backdrop-blur sm:px-8 lg:px-12">
        <div className="mx-auto grid max-w-7xl gap-4 md:grid-cols-2 lg:grid-cols-4">
          {proofPoints.map(({ label, detail, icon: Icon }) => (
            <article
              key={label}
              className="instrument-panel interactive-lift rounded-md p-5"
            >
              <Icon className="h-5 w-5 text-primary" aria-hidden />
              <h2 className="mt-4 text-base font-semibold">{label}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {detail}
              </p>
            </article>
          ))}
        </div>
        <div className="mx-auto mt-8 flex max-w-7xl flex-col items-start justify-between gap-4 rounded-md border bg-card/78 p-5 sm:flex-row sm:items-center">
          <div className="flex items-start gap-3">
            <Building2 className="mt-1 h-5 w-5 text-primary" aria-hidden />
            <div>
              <p className="font-semibold">
                Enterprise tenant review is wired.
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Signups enter the system-admin queue; approval provisions a
                workspace and first-owner invite.
              </p>
            </div>
          </div>
          <Link href="/signup" className={buttonVariants()}>
            Create tenant request
          </Link>
        </div>
      </section>
    </main>
  );
}
