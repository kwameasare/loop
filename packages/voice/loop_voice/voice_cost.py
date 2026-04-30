"""Voice call cost tracking (S388).

Each voice call accumulates four cost components:

  * **ASR seconds** — wall clock the speech-to-text recogniser ran.
  * **TTS seconds** — wall clock spent synthesising audio.
  * **LLM input/output tokens** — same as a text turn but billed in
    aggregate per call.
  * **Carrier minutes** — telephony egress (Twilio / SIP trunk).

The aggregator emits a single ``VoiceCallCostEvent`` at call end,
which the cp-api streams into the existing usage-event pipeline
(S281) so the workspace MTD rollup includes voice spend.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "VoiceCallCostAggregator",
    "VoiceCallCostEvent",
    "VoiceCostRates",
]


@dataclass(frozen=True)
class VoiceCostRates:
    asr_per_minute_micro: int = 16_000  # $0.016/min
    tts_per_minute_micro: int = 12_000  # $0.012/min
    llm_in_per_1k_tokens_micro: int = 500  # $0.0005/token in
    llm_out_per_1k_tokens_micro: int = 1_500  # $0.0015/token out
    carrier_per_minute_micro: int = 13_000  # $0.013/min PSTN egress


class VoiceCallCostEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: UUID
    call_id: UUID
    asr_seconds: float = Field(ge=0.0)
    tts_seconds: float = Field(ge=0.0)
    carrier_seconds: float = Field(ge=0.0)
    llm_tokens_in: int = Field(ge=0)
    llm_tokens_out: int = Field(ge=0)
    cost_usd_micro: int = Field(ge=0)

    @property
    def cost_usd(self) -> float:
        return self.cost_usd_micro / 1_000_000


@dataclass
class VoiceCallCostAggregator:
    """In-process aggregator the voice runtime updates as the call streams."""

    workspace_id: UUID
    call_id: UUID
    rates: VoiceCostRates = VoiceCostRates()
    asr_seconds: float = 0.0
    tts_seconds: float = 0.0
    carrier_seconds: float = 0.0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0

    def add_asr(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("asr seconds must be non-negative")
        self.asr_seconds += seconds

    def add_tts(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("tts seconds must be non-negative")
        self.tts_seconds += seconds

    def add_carrier(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("carrier seconds must be non-negative")
        self.carrier_seconds += seconds

    def add_llm_tokens(self, *, tokens_in: int, tokens_out: int) -> None:
        if tokens_in < 0 or tokens_out < 0:
            raise ValueError("token counts must be non-negative")
        self.llm_tokens_in += tokens_in
        self.llm_tokens_out += tokens_out

    def finalize(self) -> VoiceCallCostEvent:
        # All multiplication done in integer micro-USD to avoid float drift.
        asr_micro = round(self.asr_seconds / 60.0 * self.rates.asr_per_minute_micro)
        tts_micro = round(self.tts_seconds / 60.0 * self.rates.tts_per_minute_micro)
        carrier_micro = round(
            self.carrier_seconds / 60.0 * self.rates.carrier_per_minute_micro
        )
        llm_in_micro = round(
            self.llm_tokens_in / 1000.0 * self.rates.llm_in_per_1k_tokens_micro
        )
        llm_out_micro = round(
            self.llm_tokens_out / 1000.0 * self.rates.llm_out_per_1k_tokens_micro
        )
        total = asr_micro + tts_micro + carrier_micro + llm_in_micro + llm_out_micro
        return VoiceCallCostEvent(
            workspace_id=self.workspace_id,
            call_id=self.call_id,
            asr_seconds=self.asr_seconds,
            tts_seconds=self.tts_seconds,
            carrier_seconds=self.carrier_seconds,
            llm_tokens_in=self.llm_tokens_in,
            llm_tokens_out=self.llm_tokens_out,
            cost_usd_micro=total,
        )

    @staticmethod
    def total_cost_micro(events: Iterable[VoiceCallCostEvent]) -> int:
        return sum(e.cost_usd_micro for e in events)
