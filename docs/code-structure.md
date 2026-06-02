# 🗂️ Code Structure

A file-by-file map of the codebase so you can find what you need fast.

> 📎 Related: [Architecture](architecture.md) · [Agent Engine](agent-engine.md) · [Tools Reference](tools-reference.md)

---

## Top-level layout

```
Octopus-Ai/
├── backend/                 # FastAPI server + agent + tools
│   ├── main.py
│   ├── agent.py
│   ├── llm_providers.py
│   ├── config.py
│   ├── memory.py
│   ├── vector_memory.py
│   ├── requirements.txt
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── shell_tool.py
│   │   ├── file_tool.py
│   │   ├── web_tool.py
│   │   ├── code_tool.py
│   │   ├── search_tool.py
│   │   ├── image_tool.py
│   │   ├── plan_tool.py
│   │   └── delegate_tool.py
│   └── tests/               # pytest suite (conftest + test_*.py)
├── frontend/
│   ├── index.html           # markup: sidebar, chat, activity panel, settings
│   ├── css/main.css         # deep-ocean theme + components
│   └── js/app.js            # all client logic (WS, render, settings, panel)
├── data/                    # runtime, git-ignored (config, memory, vector_db, workspace)
├── docs/                    # ← you are here
├── .env.example             # environment template
├── .gitignore
└── start.sh                 # one-command launcher
```

---

## Backend

### `main.py` — server & transport
The FastAPI app and all HTTP/WS surface.
- **Middleware** (outermost → innermost): `RateLimitMiddleware` (token bucket, 120 req/min/IP) → `LocalhostRestrictionMiddleware` (rejects non-`127.0.0.1`/`::1` clients) → `CORSMiddleware` (`allow_origin_regex` for any localhost port).
- **Lifespan** registers all tools on startup.
- **WebSocket** `/ws/chat/{conv_id}` — runs `agent.process_message` as a **background task** and concurrently listens for `{"type":"stop"}` to cancel.
- **REST** — conversations CRUD + export, config, API keys, system prompt, tools list, model discovery, Google OAuth, file upload, health. (See [API Reference](api-reference.md).)
- Optional static serving of `frontend/dist` if present.

### `agent.py` — the brain
`OctopusAgent` and the global `agent` instance.
- `SYSTEM_PROMPT` — the agent's personality + operating instructions (plan → act → observe → verify).
- `process_message(conv_id, text, cancel_event)` — async generator that yields event dicts (`text`, `tool_start`, `tool_result`, `plan`, `error`, `done`).
- `_build_messages` — rebuilds the canonical message list from history (collapsing past tool turns into safe text).
- `_retrieve_memories` — RAG lookup off the event loop.
- **Native loop** — streams the model, runs tool calls in parallel (`asyncio.gather`), feeds results back, injects self-healing notes on failure.
- `_run_emulated` + `_parse_action` + `_build_emulation_prompt` — prompt-based tool calling for models without native function-calling.
- `_run_tool` / `_unknown_tool` — safe tool execution helpers.

Deep dive: **[Agent Engine](agent-engine.md)**.

### `llm_providers.py` — the model adapters
A uniform interface (`BaseLLMProvider`) with `chat_stream` (streaming) and `chat` (one-shot), plus `supports_native_tools`.
- `OpenAIProvider` — also accepts a `base_url` (so local servers can reuse it).
- `AnthropicProvider` — converts canonical messages → `tool_use`/`tool_result`, merges same-role turns, accumulates system text.
- `GeminiProvider` — converts to `function_call`/`function_response` parts; supports API key **or** OAuth token.
- `OllamaProvider` — native tool calling against `/api/chat`; converts messages to Ollama's schema; `list_models()`.
- `LocalOpenAIProvider(OpenAIProvider)` — any OpenAI-compatible server via `base_url`; `list_models()` via `/v1/models`.
- `get_provider(name, config)` — factory used by the agent.

Details: **[Providers & Models](providers-and-models.md)**.

### `config.py` — configuration & paths
- `DEFAULT_CONFIG` — the full default config shape.
- `load_config()` — merges saved `config.json` with defaults; **always pulls API keys from environment** (never from disk config).
- `save_config()` — writes `config.json` **without** secrets; API keys go to `.env` via `python-dotenv`; OAuth tokens are masked.
- `get_workspace_dir()` — the sandbox root for File/Shell, overridable via `OCTOPUS_WORKSPACE_DIR` (defaults to `data/workspace`).
- Helpers: `get_config`, `update_config`, `get_data_dir`.

Full key list: **[Configuration](configuration.md)**.

### `memory.py` — short-term memory
`MemoryManager`:
- Conversation CRUD as JSON files under `data/memory/conversations/`.
- `add_message(...)` — stores role/content (+ optional `tool_calls`, `tool_call_id`, `name`); auto-titles the first user message; **fires embeddings on a background threadpool** (non-blocking).
- `get_context_messages`, `rename_conversation`, `export_conversation` (JSON/Markdown), `delete_conversation`.
- Holds the shared `VectorMemory` instance (reused by `main.py` to avoid a second Qdrant client).

### `vector_memory.py` — long-term RAG
`VectorMemory`:
- Lazily loads Qdrant (local/embedded) + `sentence-transformers` (`all-MiniLM-L6-v2`).
- Client + model are **cached per storage path** (embedded Qdrant allows one client per folder).
- `add_conversation_message`, `search_conversations`, `store_preference`, `get_relevant_preferences`.
- A process-wide lock serializes `encode()` (the HF fast tokenizer isn't thread-safe).
- Any init failure → `enabled = False` (RAG becomes a no-op; the app still runs).

### `tools/__init__.py` — the tool framework
- `BaseTool` — abstract base: `name`, `category`, `description`, `parameters`, `async execute(**kwargs)`, `to_function_schema()`, and `enable_key` (= `category` or first token of `name`).
- `ToolRegistry` — register/get/list tools and build enabled schemas (filtered by `tools_enabled`).
- `register_all_tools()` — instantiates and registers all 8 tentacles.

### `tools/*.py` — the tentacles
| File | Tool name | Category |
| :-- | :-- | :-- |
| `shell_tool.py` | `shell_execute` | `shell` |
| `file_tool.py` | `file_operations` | `file` |
| `web_tool.py` | `web_browse` | `web` |
| `code_tool.py` | `code_execute` | `code` |
| `search_tool.py` | `search_web` | `search` |
| `image_tool.py` | `image_generate` | `image` |
| `plan_tool.py` | `update_plan` | `plan` |
| `delegate_tool.py` | `delegate_task` | `delegate` |

Each is documented (params, returns, sandboxing) in **[Tools Reference](tools-reference.md)**.

### `tests/`
- `conftest.py` — adds backend to `sys.path`; an autouse fixture points `OCTOPUS_WORKSPACE_DIR` at each test's `tmp_path`.
- `test_file_tool.py`, `test_memory.py`, `test_web_tool.py` — unit tests. Run with `pytest backend/tests`.

---

## Frontend (`frontend/`)

Zero-build vanilla. Loaded via `<script type="module">`, so serve over HTTP (not `file://`).

### `index.html`
Markup only. Key regions: sidebar (`#sidebar`), main (`#welcome-screen`, `#chat-screen`), header model switcher (`#header-provider`, `#header-model`, `#refresh-models`), Agent Activity panel (`#activity-panel`, `#activity-plan`, `#activity-timeline`), settings modal (provider cards, Tool Mode, API keys, Local Runtimes, system prompt, tentacle toggles, temperature). CDN scripts: `highlight.js`, `marked`, `DOMPurify`.

### `css/main.css`
The "deep-ocean" design system: CSS variables (`--ocean-*`, `--tentacle-*`, `--text-*`), layout, glassmorphism, animations, light theme (`[data-theme="light"]`), and the v3 additions (model switcher, activity panel, plan list, tentacle timeline).

### `js/app.js`
All client logic in one module:
- **State & init** — `state`, `els` (cached DOM refs), `DOMContentLoaded` bootstrap.
- **Config** — `loadConfig`, `applyConfig`, `saveConfigValue`, model discovery (`getModelsFor`, `populateModelSelects`, `setProvider`, `setModel`).
- **Conversations** — list/create/open/delete/rename/export.
- **WebSocket** — `connectWebSocket`, `sendMessage`, `stopStreaming`, `handleStreamEvent` (handles `text`/`tool_start`/`tool_result`/`plan`/`error`/`done`).
- **Rendering** — `renderMarkdown` (marked + DOMPurify), `enhanceCodeBlocks` (copy button + highlight), throttled streaming via `scheduleRender`.
- **Activity panel** — `renderPlan`, `addTimelineItem`, `updateTimelineItem`, `TOOL_ICONS`.
- **Settings & Google OAuth** — handlers for provider/model/tool-mode/toggles/keys/local endpoints/sign-in.

> Adding a tool or provider? Jump to the [Development Guide](development.md).
