# ⚙️ Configuration Reference

Every configuration key, where it lives, and how it's loaded.

> 📎 Related: [Providers & Models](providers-and-models.md) · [Security](security.md) · [User Guide](user-guide.md#5-settings-reference-in-app)

---

## Where configuration lives

| Location | Holds | Committed? |
| :-- | :-- | :-- |
| `.env` | **Secrets**: API keys, local key, runtime URLs (optional) | ❌ git-ignored |
| `data/config.json` | Non-secret preferences (provider, model, toggles, …) | ❌ git-ignored |
| Environment variables | Overrides for `.env`/defaults | n/a |
| In-app **Settings** | Friendly editor that writes to the above via the API | n/a |

**Golden rule:** API keys and OAuth tokens are **never** written to `config.json`. `save_config()` strips them — keys go to `.env`; OAuth access tokens are masked. `load_config()` always reads keys fresh from the environment.

---

## `.env` keys

From `.env.example`:

```bash
# Cloud providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Local runtimes
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_OPENAI_BASE_URL=http://localhost:1234/v1
LOCAL_OPENAI_API_KEY=not-needed
# LOCAL_OPENAI_MODEL=

# (optional) extra CORS origins if serving the UI elsewhere
# EXTRA_CORS_ORIGINS=
```

| Env var | Used for |
| :-- | :-- |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Cloud provider auth |
| `OLLAMA_BASE_URL` | Ollama endpoint (default `http://localhost:11434`) |
| `LOCAL_OPENAI_BASE_URL` | OpenAI-compatible local server (default `http://localhost:1234/v1`) |
| `LOCAL_OPENAI_API_KEY` | Key for that server (most need none → `not-needed`) |
| `LOCAL_OPENAI_MODEL` | Default model name for the Local provider |
| `OCTOPUS_WORKSPACE_DIR` | **Sandbox root** for File/Shell tools (default `data/workspace`) |

---

## `config.json` keys

The full default shape (`DEFAULT_CONFIG` in `config.py`):

```jsonc
{
  "llm_provider": "openai",          // openai | anthropic | gemini | ollama | local
  "model": "gpt-4o-mini",            // model id for the active provider
  "api_keys": {                       // returned MASKED by the API; persisted to .env
    "openai": "", "anthropic": "", "gemini": ""
  },
  "google_oauth": {                   // access_token is never persisted to disk
    "access_token": "", "user_name": "", "user_email": "", "authenticated": false
  },
  "google_client_id": "",            // your Google OAuth client id (for Gemini sign-in)
  "ollama_base_url": "http://localhost:11434",
  "local_openai_base_url": "http://localhost:1234/v1",
  "local_openai_api_key": "",
  "local_openai_model": "",
  "tool_mode": "auto",               // auto | native | emulated | off
  "tools_enabled": {                  // per-category toggles
    "shell": true, "file": true, "web": true, "code": true,
    "search": true, "image": true, "plan": true, "delegate": true
  },
  "max_context_messages": 50,        // context window size
  "temperature": 0.7,                // 0.0 (focused) .. 1.0 (creative)
  "theme": "dark-ocean",
  "system_prompt": ""                // empty = use the built-in SYSTEM_PROMPT
}
```

### Key notes

| Key | Notes |
| :-- | :-- |
| `llm_provider` | Which provider the agent uses. Switch live; no restart. |
| `model` | For `ollama`/`local`, models are discovered live (header ⟳). |
| `tool_mode` | `auto` = native tools when supported, else prompt emulation. See [Providers](providers-and-models.md#tool-modes). |
| `tools_enabled` | Keys are tool **categories** (= `BaseTool.enable_key`). A missing key defaults to enabled. |
| `max_context_messages` | How many recent messages are replayed to the model. |
| `system_prompt` | Overrides the default personality entirely when non-empty. |
| `google_oauth` | Populated by Google sign-in; the access token is kept in memory only. |

---

## How config is loaded & merged

```text
DEFAULT_CONFIG
   ⊕ data/config.json (if present)      → shallow merge
   ⊕ tools_enabled (deep-merged)        → missing toggles default to True
   ⊕ api_keys from environment (always) → never trust on-disk keys
= effective config
```

- `update_config(updates)` deep-merges dict values and saves.
- Editing `config.json` by hand is fine for non-secret keys; restart not required for most values (read per request), but secrets must be in `.env`/env.

---

## Tuning cheatsheet

| Want to… | Change |
| :-- | :-- |
| Use a different default model | `model` (or pick it in the header switcher) |
| Make small/local models use tools | `tool_mode: "emulated"` |
| Disable a risky tool | set its `tools_enabled.<category>` to `false` |
| Give the agent a different persona/policy | `system_prompt` |
| Remember more/less history | `max_context_messages` |
| Point File/Shell at a project folder | `OCTOPUS_WORKSPACE_DIR=/path/to/project` |
| More deterministic answers | lower `temperature` |
