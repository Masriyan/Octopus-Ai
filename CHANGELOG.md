# 📋 Changelog

All notable changes to **Octopus AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
