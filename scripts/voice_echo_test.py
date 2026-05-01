"""S371: local WebRTC echo-agent smoke."""

import argparse
import asyncio
import json
import sys
import time
from uuid import uuid4

import loop_voice as lv

DEFAULT_OFFER_SDP = "v=0\r\no=- caller IN IP4 0.0.0.0\r\n"
DEFAULT_UTTERANCE = "hello loop"


async def _round_trip(*, utterance: str, offer_sdp: str, timeout_ms: int) -> dict[str, object]:
    started = time.monotonic()
    room = f"local-voice-{uuid4().hex[:12]}"
    joined = ["caller", "echo-agent"]
    registry = lv.WebRTCSessionRegistry()
    session, answer = registry.negotiate(
        conversation_id=uuid4(),
        offer=lv.WebRTCSignal(kind="offer", sdp=offer_sdp),
        now_ms=0,
    )

    transport = lv.InMemoryRealtimeTransport()
    voice = lv.VoiceSession(
        transport=transport,
        stt=lv.InMemorySpeechToText(script=[utterance]),
        tts=lv.InMemoryTextToSpeech(),
        agent=lv.make_echo_agent(prefix="echo: "),
    )
    await transport.push_inbound(lv.AudioFrame(pcm=utterance.encode("utf-8"), sequence=0))
    await transport.end_inbound()
    turns = await voice.run()
    registry.close(session.id, now_ms=1)
    if len(turns) != 1:
        raise AssertionError(f"expected one voice turn, got {len(turns)}")

    expected = f"echo: {utterance}"
    outbound = b"".join(frame.pcm for frame in transport.outbound).decode("utf-8")
    if turns[0].agent_text != expected or outbound != expected:
        raise AssertionError(f"echo mismatch: turn={turns[0].agent_text!r} audio={outbound!r}")
    elapsed_ms = int((time.monotonic() - started) * 1000)
    if elapsed_ms > timeout_ms:
        raise AssertionError(f"heard echo after {elapsed_ms}ms, expected <= {timeout_ms}ms")
    return {
        "room": room,
        "session_id": str(session.id),
        "answer_kind": answer.kind,
        "participants_joined": joined,
        "utterance": utterance,
        "agent_text": expected,
        "outbound_text": outbound,
        "elapsed_ms": elapsed_ms,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local WebRTC voice echo smoke.")
    parser.add_argument("--utterance", default=DEFAULT_UTTERANCE)
    parser.add_argument("--offer-sdp", default=DEFAULT_OFFER_SDP)
    parser.add_argument("--timeout-ms", type=int, default=2_000)
    args = parser.parse_args(argv)
    try:
        if args.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        summary = asyncio.run(
            asyncio.wait_for(
                _round_trip(
                    utterance=args.utterance,
                    offer_sdp=args.offer_sdp,
                    timeout_ms=args.timeout_ms,
                ),
                timeout=args.timeout_ms / 1000,
            )
        )
    except TimeoutError:
        sys.stderr.write(f"voice_echo_test: FAIL no echo within {args.timeout_ms}ms\n")
        return 1
    except (AssertionError, ValueError, lv.WebRTCError) as exc:
        sys.stderr.write(f"voice_echo_test: FAIL {exc}\n")
        return 1
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
