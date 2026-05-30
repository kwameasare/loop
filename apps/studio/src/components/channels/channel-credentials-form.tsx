"use client";

/**
 * Per-channel BYOC credentials form.
 *
 * The enterprise admin picks a channel + provider and pastes the
 * provider-specific credential fields. cp encrypts them at rest with
 * Fernet (KMS-wrapped in production). The studio never reads
 * plaintext back — only confirms a value exists + when it was
 * rotated.
 */

import { KeyRound, RotateCcw, Save, Trash2 } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import { readSessionToken } from "@/lib/cp-auth-exchange";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CredentialStatus {
  has_value: boolean;
  provider?: string;
  created_at?: string;
  rotated_at?: string | null;
}

interface ProviderTemplate {
  id: string;
  label: string;
  channels: readonly string[];
  fields: readonly { key: string; placeholder: string }[];
}

const PROVIDERS: readonly ProviderTemplate[] = [
  {
    id: "twilio",
    label: "Twilio",
    channels: ["sms", "voice"],
    fields: [
      { key: "account_sid", placeholder: "AC..." },
      { key: "auth_token", placeholder: "32-char token" },
      { key: "from_number", placeholder: "+15551234567" },
    ],
  },
  {
    id: "meta_whatsapp",
    label: "Meta WhatsApp Business",
    channels: ["whatsapp"],
    fields: [
      { key: "phone_number_id", placeholder: "Numeric WABA phone ID" },
      { key: "business_account_id", placeholder: "WABA ID" },
      { key: "access_token", placeholder: "Permanent system-user token" },
      { key: "webhook_verify_token", placeholder: "Random string you set" },
    ],
  },
  {
    id: "slack",
    label: "Slack OAuth app",
    channels: ["slack"],
    fields: [
      { key: "bot_token", placeholder: "xoxb-..." },
      { key: "signing_secret", placeholder: "32 hex chars" },
      { key: "app_id", placeholder: "A0…" },
    ],
  },
  {
    id: "teams",
    label: "Microsoft Teams bot",
    channels: ["teams"],
    fields: [
      { key: "app_id", placeholder: "Azure app reg client ID" },
      { key: "app_password", placeholder: "Client secret" },
      { key: "tenant_id", placeholder: "Azure tenant UUID" },
    ],
  },
  {
    id: "telegram",
    label: "Telegram bot",
    channels: ["telegram"],
    fields: [
      { key: "bot_token", placeholder: "123456:ABC-..." },
    ],
  },
  {
    id: "discord",
    label: "Discord application",
    channels: ["discord"],
    fields: [
      { key: "bot_token", placeholder: "MT..." },
      { key: "application_id", placeholder: "snowflake" },
    ],
  },
  {
    id: "email_smtp",
    label: "SMTP relay",
    channels: ["email"],
    fields: [
      { key: "host", placeholder: "smtp.acme.com" },
      { key: "port", placeholder: "587" },
      { key: "username", placeholder: "noreply@acme.com" },
      { key: "password", placeholder: "SMTP auth password" },
    ],
  },
  {
    id: "generic",
    label: "Other / generic",
    channels: [
      "web_chat",
      "whatsapp",
      "telegram",
      "slack",
      "teams",
      "sms",
      "email",
      "voice",
      "webhook_api",
      "rcs",
      "discord",
    ],
    fields: [],
  },
];

interface ChannelCredentialsFormProps {
  agentId: string;
}

// All client cp calls go through the studio's same-origin proxy at
// ``/api/cp`` so we never hit CORS and the cp URL stays out of the
// client bundle. See ``apps/studio/src/app/api/cp/[...path]/route.ts``.
function apiBaseUrl(): string {
  return "/api/cp";
}

async function fetchStatus(
  agentId: string,
  channel: string,
  token: string,
): Promise<CredentialStatus | null> {
  const response = await fetch(
    `${apiBaseUrl()}/v1/agents/${encodeURIComponent(
      agentId,
    )}/channels/${encodeURIComponent(channel)}/credentials`,
    {
      headers: { authorization: `Bearer ${token}` },
    },
  );
  if (!response.ok) return null;
  return (await response.json()) as CredentialStatus;
}

export function ChannelCredentialsForm({
  agentId,
}: ChannelCredentialsFormProps): JSX.Element {
  const [channel, setChannel] = useState<string>("sms");
  const [providerId, setProviderId] = useState<string>("twilio");
  const [values, setValues] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<CredentialStatus | null>(null);
  const [busy, setBusy] = useState<
    | { kind: "idle" }
    | { kind: "loading" }
    | { kind: "saving" }
    | { kind: "deleting" }
    | { kind: "error"; message: string }
    | { kind: "saved" }
  >({ kind: "idle" });

  const provider = useMemo(
    () => PROVIDERS.find((p) => p.id === providerId) ?? PROVIDERS[0]!,
    [providerId],
  );

  // When channel or provider changes, reset the form fields to that
  // provider's template + refresh the saved status for the new channel.
  useEffect(() => {
    const seed: Record<string, string> = {};
    for (const field of provider.fields) seed[field.key] = "";
    setValues(seed);
  }, [provider]);

  useEffect(() => {
    let cancelled = false;
    const session = readSessionToken();
    if (!session?.access_token) return;
    setBusy({ kind: "loading" });
    fetchStatus(agentId, channel, session.access_token)
      .then((next) => {
        if (cancelled) return;
        setStatus(next);
        setBusy({ kind: "idle" });
      })
      .catch(() => {
        if (cancelled) return;
        setBusy({ kind: "idle" });
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, channel]);

  const availableProviders = PROVIDERS.filter((p) =>
    p.channels.includes(channel),
  );

  const handleField = useCallback((key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const submit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const session = readSessionToken();
      if (!session?.access_token) {
        setBusy({ kind: "error", message: "Sign in required." });
        return;
      }
      const cleaned: Record<string, string> = {};
      for (const [key, val] of Object.entries(values)) {
        const trimmed = val.trim();
        if (trimmed) cleaned[key] = trimmed;
      }
      if (Object.keys(cleaned).length === 0) {
        setBusy({
          kind: "error",
          message: "Enter at least one credential field.",
        });
        return;
      }
      setBusy({ kind: "saving" });
      try {
        const response = await fetch(
          `${apiBaseUrl()}/v1/agents/${encodeURIComponent(
            agentId,
          )}/channels/${encodeURIComponent(channel)}/credentials`,
          {
            method: "PUT",
            headers: {
              "content-type": "application/json",
              authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              provider: providerId,
              values: cleaned,
            }),
          },
        );
        if (!response.ok) {
          const text = await response.text();
          setBusy({
            kind: "error",
            message: `Save failed: HTTP ${response.status} — ${text.slice(0, 240)}`,
          });
          return;
        }
        const next = (await response.json()) as CredentialStatus;
        setStatus(next);
        setBusy({ kind: "saved" });
        // Clear local plaintext after save; nothing here should
        // retain the secret after the round-trip.
        const seed: Record<string, string> = {};
        for (const field of provider.fields) seed[field.key] = "";
        setValues(seed);
      } catch (err) {
        setBusy({
          kind: "error",
          message:
            err instanceof Error ? err.message : "Network error saving creds.",
        });
      }
    },
    [agentId, channel, provider, providerId, values],
  );

  const remove = useCallback(async () => {
    const session = readSessionToken();
    if (!session?.access_token) return;
    setBusy({ kind: "deleting" });
    try {
      const response = await fetch(
        `${apiBaseUrl()}/v1/agents/${encodeURIComponent(
          agentId,
        )}/channels/${encodeURIComponent(channel)}/credentials`,
        {
          method: "DELETE",
          headers: { authorization: `Bearer ${session.access_token}` },
        },
      );
      if (response.status !== 204 && !response.ok) {
        const text = await response.text();
        setBusy({
          kind: "error",
          message: `Delete failed: HTTP ${response.status} — ${text.slice(0, 240)}`,
        });
        return;
      }
      setStatus({ has_value: false });
      setBusy({ kind: "idle" });
    } catch (err) {
      setBusy({
        kind: "error",
        message:
          err instanceof Error ? err.message : "Network error deleting creds.",
      });
    }
  }, [agentId, channel]);

  return (
    <section
      className="instrument-panel rounded-2xl p-5"
      data-testid="channel-credentials-form"
    >
      <div className="flex items-start gap-3">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary/10 text-primary">
          <KeyRound className="h-4 w-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Provider credentials</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Bring your own Twilio / WhatsApp Business / Slack app /
            etc. Loop encrypts at rest and only decrypts inside the
            channel adapter at send time. Nobody on our end ever sees
            the plaintext.
          </p>
        </div>
      </div>

      <form className="mt-4 grid gap-3" onSubmit={submit}>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-medium uppercase tracking-wide text-muted-foreground">
              Channel
            </span>
            <select
              value={channel}
              onChange={(event) => {
                const next = event.target.value;
                setChannel(next);
                // Auto-pick a provider that supports the new channel
                // if the currently-selected one doesn't. Prefer a
                // channel-specific provider over the generic fallback.
                const current = PROVIDERS.find((p) => p.id === providerId);
                if (!current || !current.channels.includes(next)) {
                  const specific = PROVIDERS.find(
                    (p) => p.id !== "generic" && p.channels.includes(next),
                  );
                  setProviderId(specific?.id ?? "generic");
                }
              }}
              className="rounded-md border bg-background px-2 py-1.5 text-sm"
              data-testid="channel-credentials-channel"
            >
              {[
                "web_chat",
                "whatsapp",
                "telegram",
                "slack",
                "teams",
                "sms",
                "email",
                "voice",
                "webhook_api",
                "rcs",
                "discord",
              ].map((option) => (
                <option key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-medium uppercase tracking-wide text-muted-foreground">
              Provider
            </span>
            <select
              value={providerId}
              onChange={(event) => setProviderId(event.target.value)}
              className="rounded-md border bg-background px-2 py-1.5 text-sm"
              data-testid="channel-credentials-provider"
            >
              {availableProviders.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
              {/* Always allow the generic fallback so operators can
                  paste any provider's fields manually. */}
              {!availableProviders.some((p) => p.id === "generic") ? (
                <option value="generic">Other / generic</option>
              ) : null}
            </select>
          </label>
        </div>

        <div className="grid gap-2">
          {provider.fields.map((field) => (
            <label key={field.key} className="flex flex-col gap-1 text-xs">
              <span className="font-medium text-muted-foreground">
                {field.key.replace(/_/g, " ")}
              </span>
              <input
                type={
                  /token|password|secret|key/.test(field.key)
                    ? "password"
                    : "text"
                }
                autoComplete="off"
                spellCheck={false}
                value={values[field.key] ?? ""}
                onChange={(event) =>
                  handleField(field.key, event.target.value)
                }
                placeholder={field.placeholder}
                className="rounded-md border bg-background px-2 py-1.5 font-mono text-sm"
              />
            </label>
          ))}
          {provider.fields.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              The generic provider stores arbitrary key/value pairs.
              Pick a more specific provider above to get a typed form.
            </p>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="text-[0.7rem] text-muted-foreground">
            {status?.has_value ? (
              <>
                <span className="font-medium text-foreground">Stored:</span>{" "}
                provider {status.provider ?? "(unknown)"}
                {status.rotated_at ? (
                  <>
                    {" "}
                    · rotated{" "}
                    {new Date(status.rotated_at).toLocaleString(undefined, {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </>
                ) : status.created_at ? (
                  <>
                    {" "}
                    · saved{" "}
                    {new Date(status.created_at).toLocaleString(undefined, {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </>
                ) : null}
              </>
            ) : busy.kind === "loading" ? (
              "Checking…"
            ) : (
              "No credentials uploaded yet."
            )}
          </div>
          <div className="flex items-center gap-2">
            {status?.has_value ? (
              <button
                type="button"
                onClick={remove}
                disabled={busy.kind === "deleting"}
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                )}
                data-testid="channel-credentials-delete"
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Delete
              </button>
            ) : null}
            <button
              type="submit"
              disabled={busy.kind === "saving"}
              className={cn(buttonVariants({ size: "sm" }))}
              data-testid="channel-credentials-save"
            >
              {status?.has_value ? (
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              ) : (
                <Save className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              )}
              {status?.has_value ? "Rotate" : "Save"}
            </button>
          </div>
        </div>

        {busy.kind === "saved" ? (
          <p className="text-xs text-success">Credentials saved.</p>
        ) : null}
        {busy.kind === "error" ? (
          <div className="notice notice--warning" role="alert">
            <div className="notice__body">{busy.message}</div>
          </div>
        ) : null}
      </form>
    </section>
  );
}
