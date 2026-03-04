"""
Octopus AI — Tool System (Tentacles)
Base tool class and tool registry.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class for all Octopus tentacle tools."""
    name: str = ""
    description: str = ""
    parameters: dict = {}

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
            if enabled.get(t.name.split("_")[0], True)
        ]


# Global registry
registry = ToolRegistry()


def register_all_tools():
    from tools.shell_tool import ShellTool
    from tools.file_tool import FileTool
    from tools.web_tool import WebTool
    from tools.code_tool import CodeTool
    from tools.search_tool import SearchTool

    for ToolClass in [ShellTool, FileTool, WebTool, CodeTool, SearchTool]:
        registry.register(ToolClass())
