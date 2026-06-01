"""
Octopus AI — Delegate Tentacle 🐙🤝
Spawns a focused sub-agent (a "tentacle within a tentacle") that works
autonomously on a self-contained sub-task with its own tools, then returns a
concise result. Embodies the multi-arm swarm: parallel, isolated reasoning.
"""
import json
from tools import BaseTool, registry


class DelegateTool(BaseTool):
    name = "delegate_task"
    category = "delegate"
    description = (
        "Delegate a focused, self-contained sub-task to an autonomous sub-agent that "
        "works with its own tools and returns a concise result. Use for isolated "
        "sub-problems (research a topic, analyze a file, summarize a page) so the main "
        "thread stays clean. Optionally route the sub-task to a different model."
    )
    parameters = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "A clear, self-contained objective for the sub-agent.",
            },
            "context": {
                "type": "string",
                "description": "Optional background/context the sub-agent needs.",
            },
            "model": {
                "type": "string",
                "description": "Optional model override for this sub-task (multi-model routing).",
            },
        },
        "required": ["objective"],
    }

    async def execute(self, objective: str, context: str = "", model: str = None, **kwargs) -> dict:
        from config import get_config
        from llm_providers import get_provider

        config = get_config()
        try:
            provider = get_provider(config["llm_provider"], config)
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        use_model = model or config.get("model", "")
        native = getattr(provider, "supports_native_tools", True)

        # Sub-agent gets every enabled tool EXCEPT delegation (prevents recursion).
        sub_schemas = [
            s for s in registry.get_enabled_schemas(config.get("tools_enabled", {}))
            if s.get("function", {}).get("name") != "delegate_task"
        ]

        system = (
            "You are a focused Octopus sub-agent. Accomplish the objective using the "
            "available tools, then reply with a concise result summary (no preamble). "
            "Be efficient and stop as soon as the objective is met."
        )
        user = objective if not context else f"{objective}\n\nContext:\n{context}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        final_text = ""
        try:
            for _ in range(5):
                collected = ""
                tool_calls = []
                async for chunk in provider.chat_stream(
                    messages=messages,
                    tools=sub_schemas if native else None,
                    model=use_model,
                    temperature=config.get("temperature", 0.5),
                ):
                    if chunk["type"] == "text":
                        collected += chunk["content"]
                    elif chunk["type"] == "tool_calls":
                        tool_calls = chunk["tool_calls"]

                if not tool_calls:
                    final_text = collected
                    break

                messages.append({
                    "role": "assistant",
                    "content": collected or None,
                    "tool_calls": [
                        {"id": tc.get("id") or f"d{i}", "type": "function",
                         "function": {"name": tc["name"],
                                      "arguments": json.dumps(tc.get("arguments") or {}, default=str)}}
                        for i, tc in enumerate(tool_calls)
                    ],
                })
                for i, tc in enumerate(tool_calls):
                    call_id = tc.get("id") or f"d{i}"
                    inst = registry.get(tc["name"])
                    try:
                        res = (await inst.execute(**(tc.get("arguments") or {}))
                               if inst else {"status": "error", "error": f"Unknown tool: {tc['name']}"})
                    except Exception as e:
                        res = {"status": "error", "error": str(e)}
                    messages.append({
                        "role": "tool", "tool_call_id": call_id,
                        "name": tc["name"], "content": json.dumps(res, default=str),
                    })
        except Exception as e:
            return {"status": "error", "error": f"Sub-agent failed: {e}", "objective": objective}

        return {
            "status": "success",
            "objective": objective,
            "result": final_text.strip() or "(sub-agent produced no text output)",
        }
