"""S910 Twilio phone-call harness for live voice E2E verification."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol, cast

import pytest
from loop_voice.sip_twilio import StreamConfig, TwimlConfig, build_twiml


def _call_list() -> list[dict[str, str]]:
    return []


@dataclass(frozen=True, slots=True)
class TwilioCall:
    sid: str
    status: str


class TwilioVoiceClient(Protocol):
    def create_call(self, *, to_number: str, from_number: str, twiml: str) -> TwilioCall: ...


@dataclass(frozen=True, slots=True)
class TwilioRestVoiceClient:
    account_sid: str
    auth_token: str
    timeout_s: float = 10.0

    def create_call(self, *, to_number: str, from_number: str, twiml: str) -> TwilioCall:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        body = urllib.parse.urlencode(
            {
                "To": to_number,
                "From": from_number,
                "Twiml": twiml,
            }
        ).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
            payload = json.loads(response.read().decode())
        return TwilioCall(sid=str(payload["sid"]), status=str(payload.get("status", "queued")))


@dataclass(frozen=True, slots=True)
class VoiceProbeResult:
    transcript: str
    tts_audio_frames: int


class VoiceProbe(Protocol):
    def fetch_result(self, call_sid: str) -> VoiceProbeResult: ...


@dataclass(frozen=True, slots=True)
class HttpVoiceProbe:
    base_url: str
    bearer_token: str | None = None
    timeout_s: float = 60.0
    poll_interval_s: float = 1.0

    def fetch_result(self, call_sid: str) -> VoiceProbeResult:
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            try:
                payload = self._get(call_sid)
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                time.sleep(self.poll_interval_s)
                continue
            transcript = str(payload.get("transcript", ""))
            raw_frames = payload.get("tts_audio_frames", 0)
            if not isinstance(raw_frames, int | float | str):
                raise AssertionError("voice probe tts_audio_frames must be numeric")
            frames = int(raw_frames)
            if transcript and frames:
                return VoiceProbeResult(transcript=transcript, tts_audio_frames=frames)
            time.sleep(self.poll_interval_s)
        raise AssertionError(f"voice probe did not observe call {call_sid}")

    def _get(self, call_sid: str) -> dict[str, object]:
        url = f"{self.base_url.rstrip('/')}/calls/{urllib.parse.quote(call_sid)}"
        req = urllib.request.Request(url)
        if self.bearer_token:
            req.add_header("Authorization", f"Bearer {self.bearer_token}")
        with urllib.request.urlopen(req, timeout=self.poll_interval_s) as response:
            payload = json.loads(response.read().decode())
        if not isinstance(payload, dict):
            raise AssertionError("voice probe response must be a JSON object")
        return cast(dict[str, object], payload)


@dataclass(frozen=True, slots=True)
class VoicePhoneE2EResult:
    call_sid: str
    transcript: str
    tts_audio_frames: int


def run_voice_phone_call_e2e(
    *,
    client: TwilioVoiceClient,
    probe: VoiceProbe,
    to_number: str,
    from_number: str,
    stream_url: str,
    expected_utterance: str,
) -> VoicePhoneE2EResult:
    twiml = build_twiml(
        TwimlConfig(
            stream=StreamConfig(websocket_url=stream_url, track="both_tracks", name="loop-e2e"),
        )
    ).decode()
    call = client.create_call(to_number=to_number, from_number=from_number, twiml=twiml)
    result = probe.fetch_result(call.sid)
    if expected_utterance.lower() not in result.transcript.lower():
        raise AssertionError(
            f"expected {expected_utterance!r} in ASR transcript {result.transcript!r}"
        )
    if result.tts_audio_frames <= 0:
        raise AssertionError("expected at least one TTS audio frame")
    return VoicePhoneE2EResult(
        call_sid=call.sid,
        transcript=result.transcript,
        tts_audio_frames=result.tts_audio_frames,
    )


@dataclass(slots=True)
class FakeTwilioClient:
    calls: list[dict[str, str]] = field(default_factory=_call_list)

    def create_call(self, *, to_number: str, from_number: str, twiml: str) -> TwilioCall:
        self.calls.append({"to": to_number, "from": from_number, "twiml": twiml})
        return TwilioCall(sid="CA_fake_001", status="queued")


@dataclass(frozen=True, slots=True)
class FakeVoiceProbe:
    result: VoiceProbeResult

    def fetch_result(self, call_sid: str) -> VoiceProbeResult:
        assert call_sid == "CA_fake_001"
        return self.result


def test_phone_call_harness_unit_mode_dials_and_asserts_voice_path() -> None:
    client = FakeTwilioClient()
    probe = FakeVoiceProbe(
        VoiceProbeResult(transcript="caller said hello loop", tts_audio_frames=3)
    )

    result = run_voice_phone_call_e2e(
        client=client,
        probe=probe,
        to_number="+15551234567",
        from_number="+15557654321",
        stream_url="wss://voice.example.test/twilio",
        expected_utterance="hello loop",
    )

    assert result.call_sid == "CA_fake_001"
    assert result.tts_audio_frames == 3
    assert "<Stream" in client.calls[0]["twiml"]
    assert 'track="both_tracks"' in client.calls[0]["twiml"]


def test_phone_call_harness_fails_when_expected_transcript_is_missing() -> None:
    with pytest.raises(AssertionError, match="expected 'hello loop'"):
        run_voice_phone_call_e2e(
            client=FakeTwilioClient(),
            probe=FakeVoiceProbe(VoiceProbeResult(transcript="wrong words", tts_audio_frames=1)),
            to_number="+15551234567",
            from_number="+15557654321",
            stream_url="wss://voice.example.test/twilio",
            expected_utterance="hello loop",
        )


@pytest.mark.e2e
def test_twilio_live_phone_call_e2e() -> None:
    required = {
        "LOOP_TWILIO_TEST_NUMBER": os.getenv("LOOP_TWILIO_TEST_NUMBER"),
        "LOOP_TWILIO_ACCOUNT_SID": os.getenv("LOOP_TWILIO_ACCOUNT_SID"),
        "LOOP_TWILIO_AUTH_TOKEN": os.getenv("LOOP_TWILIO_AUTH_TOKEN"),
        "LOOP_TWILIO_FROM_NUMBER": os.getenv("LOOP_TWILIO_FROM_NUMBER"),
        "LOOP_TWILIO_STREAM_URL": os.getenv("LOOP_TWILIO_STREAM_URL"),
        "LOOP_TWILIO_PROBE_URL": os.getenv("LOOP_TWILIO_PROBE_URL"),
    }
    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        pytest.skip(f"live Twilio voice E2E requires {', '.join(missing)}")

    result = run_voice_phone_call_e2e(
        client=TwilioRestVoiceClient(
            account_sid=required["LOOP_TWILIO_ACCOUNT_SID"] or "",
            auth_token=required["LOOP_TWILIO_AUTH_TOKEN"] or "",
        ),
        probe=HttpVoiceProbe(
            base_url=required["LOOP_TWILIO_PROBE_URL"] or "",
            bearer_token=os.getenv("LOOP_TWILIO_PROBE_TOKEN"),
        ),
        to_number=required["LOOP_TWILIO_TEST_NUMBER"] or "",
        from_number=required["LOOP_TWILIO_FROM_NUMBER"] or "",
        stream_url=required["LOOP_TWILIO_STREAM_URL"] or "",
        expected_utterance=os.getenv("LOOP_TWILIO_EXPECTED_UTTERANCE", "hello loop"),
    )
    assert result.tts_audio_frames > 0
