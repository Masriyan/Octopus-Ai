"""
Octopus AI — LLM Providers (Brain)
Multi-provider LLM integration: OpenAI, Anthropic, Gemini, Ollama.
"""
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def chat_stream(
        self, messages: list, tools: list = None, model: str = None, temperature: float = 0.7
    ) -> AsyncGenerator[dict, None]:
        """Stream chat completions. Yields dicts with keys: type, content, tool_calls, done."""
        pass

    @abstractmethod
    async def chat(
        self, messages: list, tools: list = None, model: str = None, temperature: float = 0.7
    ) -> dict:
        """Non-streaming chat completion."""
        pass


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat_stream(self, messages, tools=None, model="gpt-4o-mini", temperature=0.7):
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self.client.chat.completions.create(**kwargs)

        tool_calls_acc = {}  # Accumulate tool call chunks

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Text content
            if delta.content:
                yield {"type": "text", "content": delta.content, "done": False}

            # Tool calls (streamed in chunks)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": ""
                        }
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_acc[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

            # Check finish reason
            if chunk.choices[0].finish_reason:
                if chunk.choices[0].finish_reason == "tool_calls" and tool_calls_acc:
                    parsed_calls = []
                    for idx in sorted(tool_calls_acc.keys()):
                        tc = tool_calls_acc[idx]
                        try:
                            args = json.loads(tc["arguments"])
                        except json.JSONDecodeError:
                            args = {}
                        parsed_calls.append({
                            "id": tc["id"],
                            "name": tc["name"],
                            "arguments": args
                        })
                    yield {"type": "tool_calls", "tool_calls": parsed_calls, "done": False}

                yield {"type": "done", "content": "", "done": True}

    async def chat(self, messages, tools=None, model="gpt-4o-mini", temperature=0.7):
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        result = {"type": "text", "content": msg.content or "", "tool_calls": []}

        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args
                })
            result["type"] = "tool_calls"

        return result


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)

    def _convert_tools_to_anthropic(self, tools: list) -> list:
        """Convert OpenAI tool format to Anthropic format."""
        converted = []
        for tool in tools:
            func = tool.get("function", tool)
            converted.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {})
            })
        return converted

    def _convert_messages_to_anthropic(self, messages: list) -> tuple:
        """Convert OpenAI message format to Anthropic format. Returns (system, messages)."""
        system = ""
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg["content"]
                    }]
                })
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})
        return system, converted

    async def chat_stream(self, messages, tools=None, model="claude-sonnet-4-20250514", temperature=0.7):
        system, conv_messages = self._convert_messages_to_anthropic(messages)

        kwargs = {
            "model": model,
            "messages": conv_messages,
            "max_tokens": 4096,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_to_anthropic(tools)

        async with self.client.messages.stream(**kwargs) as stream:
            current_tool = None

            async for event in stream:
                if event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            current_tool = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "arguments": ""
                            }
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"type": "text", "content": event.delta.text, "done": False}
                    elif hasattr(event.delta, "partial_json"):
                        if current_tool:
                            current_tool["arguments"] += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if current_tool:
                        try:
                            args = json.loads(current_tool["arguments"])
                        except json.JSONDecodeError:
                            args = {}
                        yield {
                            "type": "tool_calls",
                            "tool_calls": [{
                                "id": current_tool["id"],
                                "name": current_tool["name"],
                                "arguments": args
                            }],
                            "done": False
                        }
                        current_tool = None
                elif event.type == "message_stop":
                    yield {"type": "done", "content": "", "done": True}

    async def chat(self, messages, tools=None, model="claude-sonnet-4-20250514", temperature=0.7):
        system, conv_messages = self._convert_messages_to_anthropic(messages)

        kwargs = {
            "model": model,
            "messages": conv_messages,
            "max_tokens": 4096,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_to_anthropic(tools)

        response = await self.client.messages.create(**kwargs)

        result = {"type": "text", "content": "", "tool_calls": []}
        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })
                result["type"] = "tool_calls"

        return result


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def chat_stream(self, messages, tools=None, model="llama3.2", temperature=0.7):
        import httpx

        # Ollama uses a simpler message format
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature}
        }

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("done"):
                            yield {"type": "done", "content": "", "done": True}
                        elif data.get("message", {}).get("content"):
                            yield {
                                "type": "text",
                                "content": data["message"]["content"],
                                "done": False
                            }
                    except json.JSONDecodeError:
                        continue

    async def chat(self, messages, tools=None, model="llama3.2", temperature=0.7):
        import httpx

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            data = response.json()
            return {
                "type": "text",
                "content": data.get("message", {}).get("content", ""),
                "tool_calls": []
            }

    async def list_models(self) -> list:
        """List locally available Ollama models."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            return []


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider. Supports API key or OAuth access token."""

    def __init__(self, api_key: str = None, access_token: str = None):
        from google import genai

        if access_token:
            # Use OAuth access token
            from google.oauth2.credentials import Credentials
            credentials = Credentials(token=access_token)
            self.client = genai.Client(credentials=credentials)
        elif api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            raise ValueError("Either api_key or access_token must be provided")

    def _convert_tools_to_gemini(self, tools: list) -> list:
        """Convert OpenAI tool format to Gemini function declarations."""
        from google.genai import types

        declarations = []
        for tool in tools:
            func = tool.get("function", tool)
            params = func.get("parameters", {})

            # Convert JSON Schema properties to Gemini schema format
            gemini_props = {}
            required_fields = params.get("required", [])

            for prop_name, prop_def in params.get("properties", {}).items():
                prop_type = prop_def.get("type", "string").upper()
                type_map = {
                    "STRING": "STRING",
                    "INTEGER": "INTEGER",
                    "NUMBER": "NUMBER",
                    "BOOLEAN": "BOOLEAN",
                    "ARRAY": "ARRAY",
                    "OBJECT": "OBJECT",
                }
                gemini_props[prop_name] = types.Schema(
                    type=type_map.get(prop_type, "STRING"),
                    description=prop_def.get("description", ""),
                )

            declarations.append(types.FunctionDeclaration(
                name=func["name"],
                description=func.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties=gemini_props,
                    required=required_fields,
                ),
            ))

        return [types.Tool(function_declarations=declarations)]

    def _convert_messages_to_gemini(self, messages: list) -> tuple:
        """Convert OpenAI messages to Gemini format. Returns (system_instruction, contents)."""
        from google.genai import types

        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif role == "assistant":
                if content:
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)]
                    ))
            elif role == "tool":
                # Tool results go as user messages in Gemini
                tool_call_id = msg.get("tool_call_id", "")
                try:
                    result_data = json.loads(content) if isinstance(content, str) else content
                except json.JSONDecodeError:
                    result_data = {"result": content}

                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_call_id.split("_")[-1] if "_" in tool_call_id else "function",
                        response=result_data,
                    )]
                ))

        return system_instruction, contents

    async def chat_stream(self, messages, tools=None, model="gemini-3-flash-preview", temperature=0.7):
        from google.genai import types

        system_instruction, contents = self._convert_messages_to_gemini(messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=4096,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if tools:
            config.tools = self._convert_tools_to_gemini(tools)

        try:
            response_stream = self.client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            )

            for chunk in response_stream:
                if not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    continue

                for part in candidate.content.parts:
                    if part.text:
                        yield {"type": "text", "content": part.text, "done": False}
                    elif part.function_call:
                        fc = part.function_call
                        yield {
                            "type": "tool_calls",
                            "tool_calls": [{
                                "id": f"call_{fc.name}",
                                "name": fc.name,
                                "arguments": dict(fc.args) if fc.args else {}
                            }],
                            "done": False
                        }

            yield {"type": "done", "content": "", "done": True}

        except Exception as e:
            yield {"type": "text", "content": f"\n\n⚠️ Gemini Error: {str(e)}", "done": False}
            yield {"type": "done", "content": "", "done": True}

    async def chat(self, messages, tools=None, model="gemini-3-flash-preview", temperature=0.7):
        from google.genai import types

        system_instruction, contents = self._convert_messages_to_gemini(messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=4096,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if tools:
            config.tools = self._convert_tools_to_gemini(tools)

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        result = {"type": "text", "content": "", "tool_calls": []}

        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.text:
                    result["content"] += part.text
                elif part.function_call:
                    fc = part.function_call
                    result["tool_calls"].append({
                        "id": f"call_{fc.name}",
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {}
                    })
                    result["type"] = "tool_calls"

        return result


def get_provider(provider_name: str, config: dict) -> BaseLLMProvider:
    """Factory function to get the appropriate LLM provider."""
    if provider_name == "openai":
        api_key = config.get("api_keys", {}).get("openai", "")
        if not api_key:
            raise ValueError("OpenAI API key not configured. Set it in Settings.")
        return OpenAIProvider(api_key)
    elif provider_name == "anthropic":
        api_key = config.get("api_keys", {}).get("anthropic", "")
        if not api_key:
            raise ValueError("Anthropic API key not configured. Set it in Settings.")
        return AnthropicProvider(api_key)
    elif provider_name == "gemini":
        # Check for OAuth access token first (from Google Sign-In)
        oauth = config.get("google_oauth", {})
        if oauth.get("authenticated") and oauth.get("access_token"):
            return GeminiProvider(access_token=oauth["access_token"])
        # Fall back to API key
        api_key = config.get("api_keys", {}).get("gemini", "")
        if not api_key:
            raise ValueError("Gemini not configured. Sign in with Google or add an API key in Settings.")
        return GeminiProvider(api_key=api_key)
    elif provider_name == "ollama":
        base_url = config.get("ollama_base_url", "http://localhost:11434")
        return OllamaProvider(base_url)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
