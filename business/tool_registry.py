from __future__ import annotations

from business.tools import BusinessTool, build_default_business_tools


class BusinessToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BusinessTool] = {}

    def register_business_tool(self, tool: BusinessTool) -> None:
        self._tools[tool.name] = tool

    def list_business_tools(self) -> list[BusinessTool]:
        return [self._tools[key] for key in sorted(self._tools.keys())]

    def get_business_tool(self, name: str) -> BusinessTool | None:
        return self._tools.get(name)

    def find_tools_by_intent(self, intent_type: str) -> list[BusinessTool]:
        key = (intent_type or "").strip().lower()
        return [tool for tool in self.list_business_tools() if key in [item.lower() for item in tool.intent_types]]

    def find_tools_by_keyword(self, message: str) -> list[BusinessTool]:
        text = (message or "").lower()
        return [
            tool
            for tool in self.list_business_tools()
            if any(keyword.lower() in text for keyword in tool.keywords)
        ]

    def execute_tool(self, name: str, args: dict) -> dict:
        tool = self.get_business_tool(name)
        if tool is None:
            raise KeyError(f"Business tool not found: {name}")
        return tool.handler(args)


def _create_default_registry() -> BusinessToolRegistry:
    registry = BusinessToolRegistry()
    for tool in build_default_business_tools():
        registry.register_business_tool(tool)
    return registry


_DEFAULT_BUSINESS_TOOL_REGISTRY: BusinessToolRegistry | None = None


def get_default_business_tool_registry() -> BusinessToolRegistry:
    global _DEFAULT_BUSINESS_TOOL_REGISTRY
    if _DEFAULT_BUSINESS_TOOL_REGISTRY is None:
        _DEFAULT_BUSINESS_TOOL_REGISTRY = _create_default_registry()
    return _DEFAULT_BUSINESS_TOOL_REGISTRY


def register_business_tool(tool: BusinessTool) -> None:
    get_default_business_tool_registry().register_business_tool(tool)


def list_business_tools() -> list[BusinessTool]:
    return get_default_business_tool_registry().list_business_tools()


def get_business_tool(name: str) -> BusinessTool | None:
    return get_default_business_tool_registry().get_business_tool(name)


def find_tools_by_intent(intent_type: str) -> list[BusinessTool]:
    return get_default_business_tool_registry().find_tools_by_intent(intent_type)


def find_tools_by_keyword(message: str) -> list[BusinessTool]:
    return get_default_business_tool_registry().find_tools_by_keyword(message)
