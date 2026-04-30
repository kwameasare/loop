"""Loop runtime hot-path package."""

from loop_runtime.multi_agent import (
    AgentGraph,
    AgentRunner,
    AgentSpec,
    CallableRunner,
    HandoffStep,
    HandoffTrail,
    Merger,
    MultiAgentError,
    MultiAgentResult,
    Parallel,
    Pipeline,
    Router,
    Selector,
    Supervisor,
)
from loop_runtime.turn_executor import (
    AgentConfig,
    ToolRegistryLike,
    TurnBudget,
    TurnExecutor,
)

__version__ = "0.1.0"

__all__ = [
    "AgentConfig",
    "AgentGraph",
    "AgentRunner",
    "AgentSpec",
    "CallableRunner",
    "HandoffStep",
    "HandoffTrail",
    "Merger",
    "MultiAgentError",
    "MultiAgentResult",
    "Parallel",
    "Pipeline",
    "Router",
    "Selector",
    "Supervisor",
    "ToolRegistryLike",
    "TurnBudget",
    "TurnExecutor",
    "__version__",
]
