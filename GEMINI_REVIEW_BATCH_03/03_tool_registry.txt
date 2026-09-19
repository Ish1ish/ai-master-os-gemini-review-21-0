from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

ToolHandler = Callable[[Dict[str, Any]], Any]

@dataclass(frozen=True)
class ToolDefinition:
    tool_name: str
    version: str
    handler: ToolHandler
    enabled: bool = True
    retry_safe: bool = False

class ToolRegistry:
    """Explicit allow-list of executable tools. Unknown tools fail closed."""
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool_name: str, handler: ToolHandler, version: str = "v1",
                 enabled: bool = True, retry_safe: bool = False) -> ToolDefinition:
        name = str(tool_name or "").strip()
        ver = str(version or "").strip()
        if not name:
            raise ValueError("tool_name_required")
        if not ver:
            raise ValueError("tool_version_required")
        if not callable(handler):
            raise TypeError("tool_handler_must_be_callable")
        definition = ToolDefinition(name, ver, handler, bool(enabled), bool(retry_safe))
        self._tools[name] = definition
        return definition

    def disable(self, tool_name: str) -> bool:
        current = self._tools.get(tool_name)
        if current is None:
            return False
        self._tools[tool_name] = ToolDefinition(
            current.tool_name, current.version, current.handler, False, current.retry_safe
        )
        return True

    def get(self, tool_name: str) -> Optional[ToolDefinition]:
        return self._tools.get(str(tool_name or "").strip())

    def resolve(self, tool_name: str) -> ToolDefinition:
        definition = self.get(tool_name)
        if definition is None:
            raise KeyError("unknown_tool")
        if not definition.enabled:
            raise PermissionError("tool_disabled")
        return definition

    def list(self) -> list[Dict[str, Any]]:
        return [
            {
                "tool_name": item.tool_name,
                "version": item.version,
                "enabled": item.enabled,
                "retry_safe": item.retry_safe,
            }
            for item in sorted(self._tools.values(), key=lambda x: x.tool_name)
        ]
