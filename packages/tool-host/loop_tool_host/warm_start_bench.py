"""WarmPool warm-acquire benchmark used by S843."""

from __future__ import annotations

import time
from dataclasses import dataclass

from loop_tool_host.inmemory import InMemorySandboxFactory
from loop_tool_host.models import SandboxConfig
from loop_tool_host.pool import DEFAULT_MAX_SIZE, DEFAULT_MIN_IDLE, WarmPool

TARGET_P95_MS = 300.0


@dataclass(frozen=True, slots=True)
class WarmStartBenchResult:
    iterations: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    target_p95_ms: float
    passed: bool

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "name": "tool_host_warm_start",
            "iterations": self.iterations,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "target_p95_ms": self.target_p95_ms,
            "passed": self.passed,
        }


async def _echo(tool: str, arguments: dict[str, object]) -> dict[str, object]:
    return {"tool": tool, "args": arguments}


def _config() -> SandboxConfig:
    return SandboxConfig(
        workspace_id="warm-start-bench",
        mcp_server="echo",
        image_digest="sha256:" + "b" * 64,
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("values must be non-empty")
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * percentile))
    return round(ordered[index], 3)


async def run_warm_start_bench(
    *,
    iterations: int = 80,
    target_p95_ms: float = TARGET_P95_MS,
    min_idle: int = DEFAULT_MIN_IDLE,
    max_size: int = DEFAULT_MAX_SIZE,
) -> WarmStartBenchResult:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    pool = WarmPool(
        config=_config(),
        factory=InMemorySandboxFactory(_echo),
        min_idle=min_idle,
        max_size=max_size,
        acquire_timeout_seconds=target_p95_ms / 1000,
    )
    await pool.prewarm()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        async with pool.acquire():
            pass
        samples.append((time.perf_counter() - started) * 1000)
    p95 = _percentile(samples, 0.95)
    return WarmStartBenchResult(
        iterations=iterations,
        p50_ms=_percentile(samples, 0.50),
        p95_ms=p95,
        p99_ms=_percentile(samples, 0.99),
        target_p95_ms=target_p95_ms,
        passed=p95 < target_p95_ms,
    )
