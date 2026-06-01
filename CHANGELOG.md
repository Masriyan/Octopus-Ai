# 📋 Changelog

All notable changes to **Octopus AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] — 2026-06-01

### 🐙 The Powerful-Agent Revamp

A major upgrade turning Octopus into a genuinely autonomous, multi-model agent — plus a batch of critical bug fixes that had quietly broken the tool system.

### Fixed (critical)
- **Tool calls no longer crash.** `agent.py` used `asyncio.gather` but the `import asyncio` had been dropped in the 2.1 hardening pass, so *every* tool invocation raised `NameError`. Restored and hardened.
- **Frontend ↔ backend CORS.** The UI runs on port `5500`, but CORS only allowed `5173`/`8000`. Now any localhost origin is allowed (the backend is still localhost-only via `LocalhostRestrictionMiddleware`).
- **Multi-provider tool protocol.** Rebuilt history/tool serialization so multi-turn tool calls work correctly on OpenAI (reloaded chats), Anthropic (`tool_use`/`tool_result` reconstruction + role alternation), and Gemini (correct `function_call`/`function_response` names — no more id mangling). Removed the duplicate-user-message bug.
- **Working Stop button.** The WebSocket handler now runs the agent as a background task and listens for `stop` concurrently, so cancellation actually interrupts streaming.
- **Embedded Qdrant single-client crash** (two `MemoryManager`s opened the same DB) and **event-loop freeze** from synchronous embeddings — embeddings now run on a background thread with a tokenizer lock; vector memory degrades gracefully if unavailable.
- **Broken startup**: added the missing `.env.example`; made the File/Shell workspace configurable (`OCTOPUS_WORKSPACE_DIR`) and repaired the test suite.
- **Shell sandbox**: replaced the over-broad “any `/`” block (which refused `ls /tmp`) with a targeted destructive-command denylist, and made `unshare` network isolation fall back gracefully on hosts without user namespaces.

### Added
- **Universal tool-calling for local models.** Ollama now uses native function-calling, plus a new **Local (OpenAI-compatible)** provider for LM Studio / llama.cpp / vLLM via `base_url`. A prompt-based **tool-emulation** fallback lets *any* model (even small local ones) drive the tentacles. Configurable via **Tool Mode** (auto / native / emulated / off).
- **Planning** 🗺️ — the `update_plan` tentacle maintains a live todo checklist streamed to the UI.
- **Sub-agent delegation** 🤝 — the `delegate_task` tentacle spawns a focused, tool-capable sub-agent (with recursion guard and optional per-task model routing).
- **Agent Activity panel** — a right-hand column showing the live plan and a tentacle timeline.
- **Header model switcher** with live discovery of installed Ollama / local models.
- **Markdown overhaul** — `marked` + `DOMPurify` (tables, task lists, safe HTML) with one-pass syntax highlighting and throttled streaming renders.

---

## [2.1.0] — 2026-04-03

### 🛡️ Major Security Overhaul

A comprehensive security patch addressing 18 vulnerabilities to safely sandbox operations and prevent exfiltration and prompt injection.

### Fixed & Secured

#### 🔒 Data & Configuration Security
- **Credential Storage:** `config.json` no longer stores API keys or OAuth access tokens in plaintext. Keys are managed exclusively via the local `.env` ecosystem.
- **REST Auth & Network Locks:** Introduced a robust `LocalhostRestrictionMiddleware` to stop external network hosts from hitting the FastAPI interface on port `8000`. CORS is now strictly verified.

#### 🐙 Tentacle Sandboxing
- **Network Containment (`code_tool.py`):** Python subprocess execution is now routed through Linux `unshare -rn` to sever network capability and halt data exfiltration routines.
- **Path Isolation (`file_tool.py` & `shell_tool.py`):** Rigid limitations force directory capabilities to remain solely inside the specific `data/workspace` container folder. Out-of-bounds `../` commands are systematically denied and shell commands blocking root references are evaluated automatically.

#### 🛡️ Prompt Injection Countermeasures
- **Passive Data Fencing:** Untrusted external inputs from web sources (`web_tool.py`), DuckDuckGo results (`search_tool.py`), self-healing exception traces, and RAG contextual memory returns are isolated seamlessly within strict `<untrusted>`, `<memory>`, `<tool_failure>`, and `<external_content>` tags, guaranteeing system prompts actively reject malicious injections masquerading as instructions.
- **SSR-Failing Overrides:** Playwright navigation forcefully rejects internal networking targets like `localhost` or `127.0.0.1`.

---

## [2.0.0] — 2026-03-08

### 🚀 Expert Edition Upgrade

A massive architectural overhaul converting Octopus AI from a simple sequential chatbot into an advanced, safe, self-healing AI Swarm.

### Added

#### 🧠 Long-Term RAG Memory (Qdrant Vector DB)
- **Semantic File Parsing:** Octopus now remembers past conversations indefinitely.
- **Auto-Injection:** Context is automatically injected into the LLM prompt without manual retrieval.

#### 🐙 Multi-Agent Swarm (Parallel Execution)
- **`asyncio.gather` tool calling:** Octopus can now invoke multiple tool calls simultaneously (e.g., searching the web while reading a file), vastly decreasing response latency.

#### 🛡️ Enhanced Sanboxing & Security
- **Resource Limits:** `code_tool.py` and `shell_tool.py` are now fortified with `os.setrlimit`. Subprocesses are rigidly capped at ~256MB RAM and 10s-60s timeout limits, preventing CPU lockups and fork bombs.

#### 👁️ Active Web Automation
- **Playwright Integration:** The passive web scraper has been completely upgraded into an active Headless Chrome instance. Octopus can now click, type, and fully navigate JavaScript-rendered SPAs.

#### ⚙️ Self-Healing Auto-Remediation
- **Error Interception:** If a tool call fails during an execution loop, the Agent immediately halts, reads the Stack Trace, and passes it back to the LLM to dynamically fix its code/parameters on the fly without interrupting the user.

---

## [1.0.0] — 2025-03-05

### 🎉 Initial Release

The first public release of Octopus AI — a multi-armed AI agent with five powerful tentacles.

### Added

#### 🐙 Core Agent Engine

- Agentic loop with multi-turn tool calling (up to 10 iterations per message)
- System prompt with octopus personality and tool-awareness
- Streaming response generation via WebSocket

#### 🧠 Multi-Provider LLM Support

- **OpenAI** — GPT-4o, GPT-4o-mini, GPT-4-Turbo, GPT-3.5-Turbo
- **Anthropic** — Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus
- **Google Gemini** — Gemini 3 Flash, Gemini 3.1 Pro, Gemini 2.5 Flash/Pro
- **Ollama** — Any locally hosted model (Llama 3.2, Mistral, Code Llama, etc.)
- Hot-swappable provider switching without restart
- Google OAuth integration for Gemini (sign-in with Google)

#### 🦑 Five Tentacle Tools

- 🐚 **Shell** — Execute system commands with output capture
- 📁 **File Operations** — Read, write, list, search files and directories
- 🌐 **Web Browse** — HTTP page fetching with HTML-to-text conversion
- 💻 **Code Execution** — Sandboxed Python code runner
- 🔍 **Web Search** — DuckDuckGo search integration
- Tool permission toggles (enable/disable per tool)

#### 🎨 Frontend

- Deep-ocean dark theme with glassmorphism effects
- Animated octopus welcome screen (8-tentacle CSS animation)
- Real-time streaming chat with Markdown rendering
- Live tool execution visualization with status indicators
- Settings modal with provider, model, temperature, and API key management
- Conversation sidebar with search functionality
- Mobile-responsive design
- Google Sign-In button for Gemini OAuth

#### 💾 Backend & Persistence

- FastAPI server with WebSocket and REST endpoints
- JSON-based conversation storage
- Auto-generated conversation titles
- Configurable context window (max 50 messages)
- Configuration persistence with `data/config.json`
- Environment variable support via `.env`

#### 📚 Documentation

- Comprehensive `README.md` with architecture diagrams
- `CHANGELOG.md` (this file)
- `CONTRIBUTING.md` with contribution guidelines
- MIT License

---

[1.0.0]: https://github.com/Masriyan/Octopus-Ai/releases/tag/v1.0.0
