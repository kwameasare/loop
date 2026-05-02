"use client";

import { useState } from "react";

import {
  ASR_PROVIDERS,
  TTS_PROVIDERS,
  type AsrProvider,
  type SaveVoiceConfigFn,
  type TtsProvider,
  type VoiceConfig,
} from "@/lib/voice-config";

export interface VoiceConfigPanelProps {
  config: VoiceConfig;
  save: SaveVoiceConfigFn;
}

export function VoiceConfigPanel(props: VoiceConfigPanelProps) {
  const [asr, setAsr] = useState<AsrProvider>(props.config.asr_provider);
  const [tts, setTts] = useState<TtsProvider>(props.config.tts_provider);
  const [persistedAsr, setPersistedAsr] = useState<AsrProvider>(
    props.config.asr_provider,
  );
  const [persistedTts, setPersistedTts] = useState<TtsProvider>(
    props.config.tts_provider,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const dirty = asr !== persistedAsr || tts !== persistedTts;

  async function onSave() {
    if (saving || !dirty) return;
    setSaving(true);
    setError(null);
    try {
      const res = await props.save({ asr_provider: asr, tts_provider: tts });
      if (res.ok) {
        setPersistedAsr(asr);
        setPersistedTts(tts);
        setSavedAt(Date.now());
      } else {
        setError(res.error ?? "Could not save voice config.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      className="flex flex-col gap-6"
      data-testid="voice-config-panel"
    >
      <div className="rounded-lg border bg-white p-5">
        <h3 className="text-sm font-semibold uppercase text-zinc-500">
          Connected numbers
        </h3>
        {props.config.numbers.length === 0 ? (
          <p
            className="mt-2 text-sm text-zinc-500"
            data-testid="voice-numbers-empty"
          >
            No numbers provisioned yet.
          </p>
        ) : (
          <ul
            className="mt-3 divide-y divide-zinc-100"
            data-testid="voice-numbers"
          >
            {props.config.numbers.map((n) => (
              <li
                className="flex items-center justify-between py-2 text-sm"
                data-testid={`voice-number-${n.id}`}
                key={n.id}
              >
                <div>
                  <p className="font-mono">{n.e164}</p>
                  <p className="text-xs text-zinc-500">
                    {n.label} · {n.region}
                  </p>
                </div>
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
                  Active
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-lg border bg-white p-5">
        <h3 className="text-sm font-semibold uppercase text-zinc-500">
          Speech providers
        </h3>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase text-zinc-500">ASR</span>
            <select
              className="rounded border px-2 py-1"
              data-testid="voice-asr-select"
              onChange={(e) => setAsr(e.target.value as AsrProvider)}
              value={asr}
            >
              {ASR_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs uppercase text-zinc-500">TTS</span>
            <select
              className="rounded border px-2 py-1"
              data-testid="voice-tts-select"
              onChange={(e) => setTts(e.target.value as TtsProvider)}
              value={tts}
            >
              {TTS_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-4 flex items-center justify-end gap-3">
          {savedAt ? (
            <span
              className="text-xs text-emerald-600"
              data-testid="voice-config-saved"
              role="status"
            >
              Saved.
            </span>
          ) : null}
          <button
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="voice-config-save"
            disabled={!dirty || saving}
            onClick={() => {
              void onSave();
            }}
            type="button"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
        {error ? (
          <p
            className="mt-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
            data-testid="voice-config-error"
            role="alert"
          >
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
