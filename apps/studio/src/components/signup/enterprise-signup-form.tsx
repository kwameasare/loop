"use client";

import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  LockKeyhole,
  MessagesSquare,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  createEnterpriseSignup,
  type EnterpriseSignupResponse,
} from "@/lib/enterprise-signup";

const channelOptions = [
  "web",
  "WhatsApp",
  "Telegram",
  "Slack",
  "Teams",
  "SMS",
  "email",
  "voice",
] as const;

const complianceOptions = [
  "SSO",
  "SCIM",
  "SOC2",
  "data residency",
  "audit export",
  "BYOK",
] as const;

function toggle(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value];
}

export function EnterpriseSignupForm() {
  const [organizationName, setOrganizationName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [companySize, setCompanySize] = useState("100-500");
  const [region, setRegion] = useState("na-east");
  const [primaryUseCase, setPrimaryUseCase] = useState("");
  const [channels, setChannels] = useState<string[]>(["web", "WhatsApp"]);
  const [compliance, setCompliance] = useState<string[]>(["SSO", "SOC2"]);
  const [ssoRequired, setSsoRequired] = useState(true);
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "error"; message: string }
    | { kind: "success"; response: EnterpriseSignupResponse }
  >({ kind: "idle" });

  const slugPreview = useMemo(
    () =>
      organizationName
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9-]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .replace(/-{2,}/g, "-")
        .slice(0, 64) || "workspace",
    [organizationName],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus({ kind: "submitting" });
    try {
      const response = await createEnterpriseSignup({
        organization_name: organizationName,
        workspace_slug: slugPreview,
        admin_name: adminName,
        admin_email: adminEmail,
        company_size: companySize,
        region,
        primary_use_case: primaryUseCase,
        channel_priorities: channels,
        compliance_needs: compliance,
        sso_required: ssoRequired,
      });
      setStatus({ kind: "success", response });
    } catch (error) {
      setStatus({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Could not submit enterprise signup.",
      });
    }
  }

  if (status.kind === "success") {
    const signup = status.response.signup;
    return (
      <section
        className="instrument-panel mx-auto w-full max-w-3xl rounded-md p-6"
        data-testid="enterprise-signup-success"
      >
        <div className="flex items-start gap-4">
          <span className="grid h-11 w-11 place-items-center rounded-md bg-primary/15 text-primary">
            <CheckCircle2 className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-2xl font-semibold">Tenant request received</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {signup.organization_name} is now queued for system-admin review.
              Approval provisions the workspace and first owner invite.
            </p>
          </div>
        </div>
        <dl className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            ["Signup", signup.id],
            ["Workspace slug", signup.workspace_slug],
            ["Status", signup.status.replace(/_/g, " ")],
          ].map(([label, value]) => (
            <div key={label} className="rounded-md border bg-background/72 p-3">
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="mt-1 font-mono text-sm">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/login?returnTo=/system/admin"
            className={buttonVariants()}
          >
            Open system admin
            <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
          </Link>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Back to welcome
          </Link>
        </div>
      </section>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="instrument-panel mx-auto grid w-full max-w-6xl gap-6 rounded-md p-5 lg:grid-cols-[minmax(0,1fr)_22rem]"
      data-testid="enterprise-signup-form"
    >
      <div className="space-y-5">
        <div>
          <h1 className="text-3xl font-semibold">Start enterprise signup</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Create a tenant request with enough context for system admins to
            provision the workspace, owner invite, SSO path, and channel plan.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium">Organization</span>
            <input
              required
              value={organizationName}
              onChange={(event) => setOrganizationName(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
              placeholder="Acme Bank"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Admin name</span>
            <input
              required
              value={adminName}
              onChange={(event) => setAdminName(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
              placeholder="Maya Chen"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Admin email</span>
            <input
              required
              type="email"
              value={adminEmail}
              onChange={(event) => setAdminEmail(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
              placeholder="maya@acme.com"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Company size</span>
            <select
              value={companySize}
              onChange={(event) => setCompanySize(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
            >
              {["1-50", "51-100", "100-500", "500-1000", "1000-5000", "5000+"].map(
                (size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ),
              )}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Data region</span>
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
            >
              <option value="na-east">North America East</option>
              <option value="eu-west">Europe West</option>
              <option value="af-south">Africa South</option>
              <option value="ap-south">Asia Pacific South</option>
            </select>
          </label>
          <div className="rounded-md border bg-background/72 p-3">
            <p className="text-xs text-muted-foreground">Workspace slug</p>
            <p className="mt-1 font-mono text-sm">{slugPreview}</p>
          </div>
        </div>

        <label className="block space-y-1 text-sm">
          <span className="font-medium">Primary use case</span>
          <textarea
            required
            minLength={8}
            value={primaryUseCase}
            onChange={(event) => setPrimaryUseCase(event.target.value)}
            className="min-h-24 w-full rounded-md border bg-background px-3 py-2"
            placeholder="Migrate support agents from Botpress and operate WhatsApp, web, and voice under approval gates."
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <fieldset className="rounded-md border bg-background/72 p-4">
            <legend className="px-1 text-sm font-medium">Priority channels</legend>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {channelOptions.map((channel) => (
                <label key={channel} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={channels.includes(channel)}
                    onChange={() => setChannels((current) => toggle(current, channel))}
                  />
                  {channel}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="rounded-md border bg-background/72 p-4">
            <legend className="px-1 text-sm font-medium">Governance needs</legend>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {complianceOptions.map((item) => (
                <label key={item} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={compliance.includes(item)}
                    onChange={() => setCompliance((current) => toggle(current, item))}
                  />
                  {item}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        <label className="flex items-center gap-2 rounded-md border bg-background/72 p-3 text-sm">
          <input
            type="checkbox"
            checked={ssoRequired}
            onChange={(event) => setSsoRequired(event.target.checked)}
          />
          SSO is required before production access.
        </label>

        {status.kind === "error" ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/35 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {status.message}
          </p>
        ) : null}
      </div>

      <aside className="grid content-start gap-4">
        <div className="rounded-md border bg-background/72 p-4">
          <Building2 className="h-5 w-5 text-primary" aria-hidden />
          <p className="mt-3 font-semibold">What gets created</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            A reviewed tenant request. System approval creates the workspace,
            audit event, and first owner invitation.
          </p>
        </div>
        <div className="rounded-md border bg-background/72 p-4">
          <MessagesSquare className="h-5 w-5 text-primary" aria-hidden />
          <p className="mt-3 font-semibold">Channels are peers</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Voice is one channel. Chat, messaging, email, and webhooks get the
            same readiness and governance treatment.
          </p>
        </div>
        <div className="rounded-md border bg-background/72 p-4">
          <LockKeyhole className="h-5 w-5 text-primary" aria-hidden />
          <p className="mt-3 font-semibold">No silent tenant creation</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Admin review separates public signup intent from workspace access
            and owner onboarding.
          </p>
        </div>
        <Button
          type="submit"
          size="lg"
          disabled={status.kind === "submitting"}
          className="w-full"
        >
          {status.kind === "submitting" ? "Submitting..." : "Submit tenant request"}
        </Button>
      </aside>
    </form>
  );
}
