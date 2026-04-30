"""Loop MCP client.

Two surfaces:

* The ``@tool`` decorator for in-process auto-MCP'd Python functions
  (skill: implement-mcp-tool / Path A). It introspects the wrapped
  function's signature plus docstring and produces an MCP ``Tool``
  descriptor with a JSON-Schema input contract.
* A process-local :class:`ToolRegistry` plus a stdio JSON-RPC transport
  for talking to out-of-process MCP servers (Path B). The transport is
  intentionally a thin client -- sandboxing belongs to dp-tool-host
  (S014/S028).

The wire format mirrors the MCP spec (``tools/list`` + ``tools/call``)
so the same descriptors are valid against either path. ADR-003 fixes
this universal ABI.
"""

from loop_mcp.decorator import Tool, tool
from loop_mcp.registry import ToolRegistry, default_registry
from loop_mcp.schema import build_input_schema
from loop_mcp.transport import StdioMcpClient

__all__ = [
    "StdioMcpClient",
    "Tool",
    "ToolRegistry",
    "build_input_schema",
    "default_registry",
    "tool",
]
