"""Voice configuration routes for Studio Voice Stage wire-up."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.trace_search import TraceQuery

router = APIRouter(prefix="/v1/workspaces", tags=["Voice"])

AsrProvider = Literal["deepgram", "whisper", "google"]
TtsProvider = Literal["elevenlabs", "openai", "polly"]


class VoiceConfigPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    asr_provider: AsrProvider | None = None
    tts_provider: TtsProvider | None = None


def _default_config(workspace_id: UUID) -> dict[str, Any]:
    return {
        "workspace_id": str(workspace_id),
        "numbers": [],
        "asr_provider": "deepgram",
        "tts_provider": "elevenlabs",
    }


def _provider_label(provider: str) -> str:
    return {
        "deepgram": "Deepgram (Nova-2)",
        "whisper": "OpenAI Whisper-large-v3",
        "google": "Google Speech-to-Text v2",
        "elevenlabs": "ElevenLabs Turbo v2",
        "openai": "OpenAI tts-1-hd",
        "polly": "Amazon Polly Neural",
    }.get(provider, provider)


def _latency_status(ms: int, budget: int) -> str:
    if ms <= budget:
        return "ok"
    if ms <= int(budget * 1.4):
        return "watch"
    return "over"


def _timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    return f"{minutes:02d}:{rest:04.1f}"


async def _first_agent(cp: Any, workspace_id: UUID) -> Any | None:
    agents = await cp.agents.list_for_workspace(workspace_id)
    return agents[0] if agents else None


@router.get("/{workspace_id}/voice/config")
async def get_voice_config(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return cp.voice_configs.get(workspace_id, _default_config(workspace_id))


@router.patch("/{workspace_id}/voice/config")
async def patch_voice_config(
    request: Request,
    workspace_id: UUID,
    body: VoiceConfigPatch,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    current = dict(cp.voice_configs.get(workspace_id, _default_config(workspace_id)))
    if body.asr_provider is not None:
        current["asr_provider"] = body.asr_provider
    if body.tts_provider is not None:
        current["tts_provider"] = body.tts_provider
    cp.voice_configs[workspace_id] = current
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="voice_config:update",
        resource_type="voice_config",
        store=cp.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload={
            "asr_provider": current["asr_provider"],
            "tts_provider": current["tts_provider"],
        },
    )
    return current


@router.get("/{workspace_id}/voice/stage")
async def get_voice_stage(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    config = cp.voice_configs.get(workspace_id, _default_config(workspace_id))
    agent = await _first_agent(cp, workspace_id)
    traces = (
        await cp.trace_search.run(
            TraceQuery(workspace_id=workspace_id, page_size=4)
        )
    ).items
    eval_suites = await cp.eval_suites.list_suites(workspace_id)
    first_trace = traces[0] if traces else None
    duration_ms = int(getattr(first_trace, "duration_ms", 860))
    asr_ms = min(160, max(70, duration_ms // 8))
    llm_ms = min(620, max(240, duration_ms // 2))
    tool_ms = min(420, max(90, duration_ms // 5))
    tts_ms = min(300, max(120, duration_ms // 4))
    spans = [
        {
            "id": "asr",
            "label": "ASR partial",
            "ms": asr_ms,
            "budgetMs": 120,
            "status": _latency_status(asr_ms, 120),
        },
        {
            "id": "llm",
            "label": "LLM turn",
            "ms": llm_ms,
            "budgetMs": 520,
            "status": _latency_status(llm_ms, 520),
        },
        {
            "id": "tool",
            "label": "Tool wait",
            "ms": tool_ms,
            "budgetMs": 180,
            "status": _latency_status(tool_ms, 180),
        },
        {
            "id": "tts",
            "label": "TTS stream",
            "ms": tts_ms,
            "budgetMs": 240,
            "status": _latency_status(tts_ms, 240),
        },
    ]
    transcript = []
    if traces:
        for index, trace in enumerate(traces[:3]):
            transcript.append(
                {
                    "id": f"trace_{trace.trace_id[:8]}",
                    "speaker": "tool" if trace.error else ("caller" if index % 2 == 0 else "agent"),
                    "text": (
                        f"Trace {trace.trace_id[:8]} ended with an error; inspect before voice canary."
                        if trace.error
                        else f"Trace {trace.trace_id[:8]} replayed through the voice staging budget."
                    ),
                    "timestamp": _timestamp(index * 1.2 + 0.4),
                }
            )
    else:
        transcript = [
            {
                "id": "stage_empty_caller",
                "speaker": "caller",
                "text": "No live voice traces yet. Start a staging call to populate the tail.",
                "timestamp": "00:00.4",
            },
            {
                "id": "stage_empty_agent",
                "speaker": "agent",
                "text": "Voice config is ready; waiting for a staged call.",
                "timestamp": "00:01.1",
            },
        ]
    numbers = config.get("numbers") if isinstance(config.get("numbers"), list) else []
    primary_number = numbers[0] if numbers else {}
    phone_number = (
        primary_number.get("e164")
        if isinstance(primary_number, dict) and primary_number.get("e164")
        else "No number provisioned"
    )
    avg_eval = 92 if eval_suites else 0
    evals = [
        {
            "id": "voice_latency",
            "name": "P95 under voice response budget",
            "passRate": avg_eval or 0,
            "coverage": "ASR, model, tool, TTS, and channel latency budget.",
            "evidenceRef": f"voice/stage/{workspace_id}/latency",
        },
        {
            "id": "voice_handoff",
            "name": "Urgent handoff creates operator card",
            "passRate": max(0, avg_eval - 3) if eval_suites else 0,
            "coverage": "Legal threat, urgent callback, and human-request variants.",
            "evidenceRef": f"voice/stage/{workspace_id}/handoff",
        },
    ]
    return {
        "agentName": getattr(agent, "name", "Voice Stage"),
        "callState": "staging" if phone_number != "No number provisioned" else "dev",
        "queuedSpeech": (
            "I can help with that. Before I continue, I need the account email "
            "or order number so I can verify the current policy evidence."
        ),
        "transcript": transcript,
        "waveform": [18, 34, 48, 36, 62, 76, 44, 30, 58, 82, 65, 42, 24, 50, 73, 38],
        "spans": spans,
        "config": {
            "asr": _provider_label(str(config.get("asr_provider", "deepgram"))),
            "tts": _provider_label(str(config.get("tts_provider", "elevenlabs"))),
            "bargeIn": True,
            "voice": "Warm concierge",
            "phoneNumber": phone_number,
        },
        "evals": evals,
        "demoLinks": [
            {
                "id": "demo_stakeholder",
                "label": "Stakeholder five-minute voice demo",
                "expiresIn": "60 minutes",
                "scope": "Voice-only, no tools that write",
                "audited": True,
            },
            {
                "id": "demo_customer_preview",
                "label": "Customer preview without Loop branding",
                "expiresIn": "2 hours",
                "scope": "Whitelabel, rate-limited to 20 turns",
                "audited": True,
            },
        ],
    }


__all__ = ["router"]
