"""
Octopus AI — Agent Engine 🐙
Core agent loop: receive message → call LLM → execute tools → stream response.
"""
import json
import traceback
from typing import AsyncGenerator
from config import get_config
from memory import MemoryManager
from llm_providers import get_provider
from tools import registry, register_all_tools

# System prompt that defines Octopus's personality
SYSTEM_PROMPT = """You are **Octopus AI** 🐙 — a powerful, multi-capable AI agent with many arms (tools) that can reach into different domains simultaneously.

## Your Personality
- You are helpful, proactive, and knowledgeable
- You have a subtle octopus theme — you're clever, adaptable, and resourceful
- You explain your actions clearly and show your work
- When using tools, you describe what you're doing and why

## Your Tentacles (Tools)
You have access to these tools:
1. **Shell** 🐚 — Execute commands on the user's system
2. **File Operations** 📁 — Read, write, list, and search files
3. **Web Browse** 🌐 — Fetch and read web pages
4. **Code Execute** 💻 — Run Python code
5. **Web Search** 🔍 — Search the internet

## Guidelines
- Use tools proactively when they would help answer the user's question
- Always prefer using tools to give accurate, real-time information rather than guessing
- For file operations, always use absolute paths when possible
- For shell commands, be mindful of the user's OS and environment
- When browsing the web, summarize the key content clearly
- If a task requires multiple tools, use them in logical sequence
- If a tool fails, explain what happened and try an alternative approach
- Keep responses concise but thorough
"""


class OctopusAgent:
    def __init__(self):
        self.memory = MemoryManager()
        self._tools_registered = False

    def _ensure_tools(self):
        if not self._tools_registered:
            register_all_tools()
            self._tools_registered = True

    def _build_messages(self, conv_id: str, user_message: str, config: dict) -> list:
        """Build the message array for the LLM."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history
        history = self.memory.get_context_messages(
            conv_id, max_messages=config.get("max_context_messages", 50)
        )
        for msg in history:
            role = msg["role"]
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg["content"]})
            elif role == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg["content"],
                    "tool_call_id": msg.get("tool_call_id", "")
                })

        # Add current user message
        messages.append({"role": "user", "content": user_message})
        return messages

    async def process_message(
        self, conv_id: str, user_message: str
    ) -> AsyncGenerator[dict, None]:
        """Process a user message and yield streaming response events."""
        self._ensure_tools()
        config = get_config()

        # Save user message
        self.memory.add_message(conv_id, "user", user_message)

        # Build messages
        messages = self._build_messages(conv_id, user_message, config)

        # Get LLM provider
        try:
            provider = get_provider(config["llm_provider"], config)
        except ValueError as e:
            error_msg = str(e)
            self.memory.add_message(conv_id, "assistant", f"⚠️ {error_msg}")
            yield {"type": "error", "content": error_msg}
            return

        # Get tool schemas
        tool_schemas = registry.get_enabled_schemas(config.get("tools_enabled", {}))

        # Agent loop: LLM may request tool calls, which we execute and feed back
        max_iterations = 10
        full_response = ""

        for iteration in range(max_iterations):
            try:
                # Determine if we should use tools (Ollama doesn't support them well)
                use_tools = tool_schemas if config["llm_provider"] != "ollama" else None

                collected_text = ""
                tool_calls = []

                async for chunk in provider.chat_stream(
                    messages=messages,
                    tools=use_tools,
                    model=config.get("model", "gpt-4o-mini"),
                    temperature=config.get("temperature", 0.7)
                ):
                    if chunk["type"] == "text":
                        collected_text += chunk["content"]
                        yield {"type": "text", "content": chunk["content"]}
                    elif chunk["type"] == "tool_calls":
                        tool_calls = chunk["tool_calls"]
                    elif chunk["type"] == "done":
                        pass

                # If no tool calls, we're done
                if not tool_calls:
                    full_response += collected_text
                    break

                # Add assistant message with tool calls to context
                full_response += collected_text
                if collected_text:
                    messages.append({"role": "assistant", "content": collected_text})

                # Execute tool calls
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    tool_id = tc.get("id", f"call_{tool_name}")

                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "arguments": tool_args,
                        "id": tool_id
                    }

                    # Execute the tool
                    tool_instance = registry.get(tool_name)
                    if tool_instance:
                        try:
                            result = await tool_instance.execute(**tool_args)
                        except Exception as e:
                            result = {"status": "error", "error": str(e)}
                    else:
                        result = {"status": "error", "error": f"Unknown tool: {tool_name}"}

                    result_str = json.dumps(result, indent=2, default=str)

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": result,
                        "id": tool_id
                    }

                    # Add tool call and result to messages for next iteration
                    # For OpenAI format
                    if config["llm_provider"] == "openai":
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(tool_args)
                                }
                            }]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result_str
                        })
                    else:
                        # Anthropic / Ollama — use tool role
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result_str
                        })

                    # Save tool call to memory
                    self.memory.add_message(
                        conv_id, "tool", result_str,
                        tool_calls=[{"name": tool_name, "arguments": tool_args}]
                    )

            except Exception as e:
                error_msg = f"Error during processing: {str(e)}\n{traceback.format_exc()}"
                yield {"type": "error", "content": str(e)}
                full_response += f"\n\n⚠️ Error: {str(e)}"
                break

        # Save the full assistant response
        if full_response.strip():
            self.memory.add_message(conv_id, "assistant", full_response)

        yield {"type": "done", "content": ""}


# Global agent instance
agent = OctopusAgent()
