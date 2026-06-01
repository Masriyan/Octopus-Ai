"""
Octopus AI — Tool System (Tentacles)
Base tool class and tool registry.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class for all Octopus tentacle tools."""
    name: str = ""
    # Permission category used by tools_enabled toggles. Defaults to the first
    # token of the tool name (e.g. "shell_execute" -> "shell").
    category: str = ""
    description: str = ""
    parameters: dict = {}

    @property
    def enable_key(self) -> str:
        return self.category or self.name.split("_")[0]

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Execute the tool and return results."""
        pass

    def to_function_schema(self) -> dict:
        """Convert to OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ToolRegistry:
    """Registry of all available tentacle tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def get_function_schemas(self) -> list[dict]:
        return [t.to_function_schema() for t in self._tools.values()]

    def get_enabled_schemas(self, enabled: dict) -> list[dict]:
        return [
            t.to_function_schema()
            for t in self._tools.values()
            if enabled.get(t.enable_key, True)
        ]


# Global registry
registry = ToolRegistry()


def register_all_tools():
    from tools.shell_tool import ShellTool
    from tools.file_tool import FileTool
    from tools.web_tool import WebTool
    from tools.code_tool import CodeTool
    from tools.search_tool import SearchTool
    from tools.image_tool import ImageTool
    from tools.plan_tool import PlanTool
    from tools.delegate_tool import DelegateTool

    for ToolClass in [ShellTool, FileTool, WebTool, CodeTool, SearchTool,
                      ImageTool, PlanTool, DelegateTool]:
        tool = ToolClass()
        if tool.name not in registry._tools:
            registry.register(tool)
