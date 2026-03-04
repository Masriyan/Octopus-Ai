# 📋 Changelog

All notable changes to **Octopus AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
