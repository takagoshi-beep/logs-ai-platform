from __future__ import annotations

from typing import Any

from tools.definitions import ToolDefinition


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, tool_name: str) -> ToolDefinition | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "input_schema": item.input_schema,
                "output_schema": item.output_schema,
            }
            for item in self._tools.values()
        ]

    def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        tool = self.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
        return tool.handler(args)


_DEFAULT_REGISTRY: ToolRegistry | None = None


def get_default_registry() -> ToolRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        from tools.executor import register_default_tools

        registry = ToolRegistry()
        register_default_tools(registry)
        _DEFAULT_REGISTRY = registry
    return _DEFAULT_REGISTRY
