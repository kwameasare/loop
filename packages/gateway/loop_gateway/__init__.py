"""Loop LLM gateway: the only chokepoint for outbound LLM traffic.

Streaming-first by contract. Every provider yields ``GatewayEvent``s as the
upstream response arrives -- buffering whole responses is forbidden (ADR-022).
"""

from loop_gateway.cost import COST_TABLE, ModelRate, cost_for, with_markup
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayMessage,
    GatewayRequest,
    Provider,
    Role,
    ToolCall,
    ToolSpec,
    Usage,
)

__all__ = [
    "COST_TABLE",
    "GatewayDelta",
    "GatewayDone",
    "GatewayError",
    "GatewayEvent",
    "GatewayMessage",
    "GatewayRequest",
    "ModelRate",
    "Provider",
    "Role",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "cost_for",
    "with_markup",
]
