# 🧠 Providers & Models

Octopus speaks to five kinds of model backend through one uniform interface. This guide covers each, plus the **tool calling modes** that make even small local models tool-capable.

> 📎 Related: [Configuration](configuration.md) · [Agent Engine](agent-engine.md) · [Code Structure](code-structure.md#llm_providerspy--the-model-adapters)

---

## The provider interface

Every provider implements `BaseLLMProvider` in `backend/llm_providers.py`:

```python
class BaseLLMProvider:
    supports_native_tools: bool = True
    async def chat_stream(self, messages, tools=None, model=None, temperature=0.7): ...  # yields events
    async def chat(self, messages, tools=None, model=None, temperature=0.7): ...          # one-shot
```

`chat_stream` yields dicts the agent understands:
- `{"type": "text", "content": "…"}`
- `{"type": "tool_calls", "tool_calls": [{"id","name","arguments"}]}`
- `{"type": "done"}`

`get_provider(name, config)` is the factory that the agent calls.

---

## Supported providers

| Provider (`llm_provider`) | Class | Auth | Native tools | Notes |
| :-- | :-- | :-- | :-- | :-- |
| `openai` | `OpenAIProvider` | API key | ✅ | GPT-4o family |
| `anthropic` | `AnthropicProvider` | API key | ✅ | Claude (Sonnet/Haiku/Opus) |
| `gemini` | `GeminiProvider` | API key **or** Google OAuth | ✅ | Gemini 3 / 2.5 |
| `ollama` | `OllamaProvider` | none (local) | ✅ | native tool calling via `/api/chat` |
| `local` | `LocalOpenAIProvider` | optional | ✅ | any OpenAI-compatible server (`base_url`) |

### OpenAI
Set `OPENAI_API_KEY` (or in Settings). Models: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`. Also used internally by the **Image** tentacle (DALL·E).

### Anthropic
Set `ANTHROPIC_API_KEY`. The provider rebuilds `tool_use`/`tool_result` blocks, **merges consecutive same-role turns** (Anthropic requires strict alternation), and accumulates all system messages into one.

### Google Gemini
Two ways in:
1. **API key** — `GEMINI_API_KEY`.
2. **Google Sign-In** — set a Google OAuth **Client ID** in Settings, click *Sign in with Google*. The access token is held in memory only (never written to disk) and auto-selects Gemini.

The provider maps tool results to `function_response` using the **stored function name** (so multi-tool turns stay correct).

### Ollama (local, free)
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2        # choose a tool-capable model for best results
ollama serve               # usually auto-started
```
- Default endpoint `http://localhost:11434` (`OLLAMA_BASE_URL`).
- **Native tool calling** is used — Octopus passes the OpenAI tool schema and parses `message.tool_calls`.
- Installed models are **auto-discovered**: pick **Ollama**, then hit the ⟳ refresh in the header.

### Local (OpenAI-compatible)
For **LM Studio**, **llama.cpp** (`server`), **vLLM**, **text-generation-webui**, etc.
1. Start the server, e.g. LM Studio → "Local Server" on `http://localhost:1234/v1`.
2. Settings → **Local Runtimes**: set base URL, optional API key, and model name.
3. Select the **Local** provider. Models are listed via `/v1/models` (⟳ to refresh).

---

## Tool modes

Configured by `tool_mode` (Settings → **Tool Calling Mode**). It decides *how* the agent drives tools:

| Mode | Behavior |
| :-- | :-- |
| `auto` *(default)* | Use **native** function-calling if the provider/model supports it, otherwise fall back to **emulation**. |
| `native` | Require native function-calling. If unsupported, tools are disabled for that turn. |
| `emulated` | Always use prompt-based emulation (works with *any* text model). |
| `off` | No tools — plain chat. |

### What emulation does
For models without native tools, the agent injects a small protocol into the prompt:

> To use a tool, reply with ONLY:
> ```action
> {"tool": "<name>", "arguments": { … }}
> ```
> …then you'll receive an `<observation>` with the result.

The agent buffers the model's reply, parses the action (so the raw JSON never reaches the UI), runs the tool, feeds back the observation, and loops — up to 8 steps. This is what lets a small local model still browse the web, run code, etc.

Details and the loop internals: **[Agent Engine](agent-engine.md#emulated-tool-calling)**.

---

## Choosing a setup

| You want… | Use |
| :-- | :-- |
| Best quality, easiest | OpenAI / Anthropic / Gemini (cloud, API key) |
| Free & private, good tooling | **Ollama** with a tool-capable model + `tool_mode: auto` |
| A specific local server / GPU stack | **Local** (LM Studio / vLLM) via `base_url` |
| A tiny model that can't do native tools | any provider + `tool_mode: emulated` |
| No API key but have a Google account | **Gemini via Google Sign-In** |

---

## Adding a new provider

1. Subclass `BaseLLMProvider`; implement `chat_stream` + `chat`; set `supports_native_tools`.
2. Convert the canonical OpenAI-style messages to your API's format (see the Anthropic/Gemini converters for reference).
3. Add a branch in `get_provider(...)`.
4. (Optional) add `list_models()` and a case in `GET /api/models/{provider}`.
5. Add it to the frontend: a provider `<option>`/card and `getModelsFor`.

Step-by-step: **[Development Guide](development.md#adding-a-provider)**.
