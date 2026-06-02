# 🧭 User Guide

Everything you need to install, run, and use **Octopus AI** day-to-day.

> 📎 Related: [Providers & Models](providers-and-models.md) · [Configuration](configuration.md) · [Security](security.md)

---

## 1. Requirements

| Requirement | Version |
| :-- | :-- |
| Python | 3.10 or higher |
| pip | latest recommended |
| A model | At least one of: OpenAI / Anthropic / Gemini API key, **or** a local runtime (Ollama / LM Studio / llama.cpp / vLLM) — local is free |
| Browser | Any modern browser (Chrome, Firefox, Edge, Safari) |

Optional but recommended for full power:
- **Playwright** browser (`playwright install chromium`) for the Web Browse tentacle.
- **Ollama** or an OpenAI-compatible server for free/local/private models.

---

## 2. Installation

### Quick start (one command)

```bash
git clone https://github.com/Masriyan/Octopus-Ai.git
cd Octopus-Ai
chmod +x start.sh
./start.sh
```

`start.sh` will:
1. create a `venv/` virtual environment,
2. install `backend/requirements.txt`,
3. copy `.env.example` → `.env` (if missing),
4. start the **backend** on `http://localhost:8000`,
5. start the **frontend** on `http://localhost:5500`.

Then open **http://localhost:5500**. 🎉

### Manual setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium          # optional, for Web Browse

cp .env.example .env                 # then edit and add keys if you want

# Terminal 1 — backend
cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — frontend
cd frontend && python3 -m http.server 5500
```

> 💡 You don't *have* to put keys in `.env` — you can add them later from the in-app **Settings** panel.

---

## 3. The interface at a glance

```
┌───────────────┬──────────────────────────────┬──────────────────┐
│   Sidebar     │          Chat                │  Agent Activity  │
│               │  ┌────────────────────────┐  │                  │
│ + New Chat    │  │  messages / streaming  │  │  🗺️ Plan         │
│ 🔎 search     │  │                        │  │   ● step 1       │
│ conversations │  │                        │  │   ◐ step 2       │
│   ...         │  └────────────────────────┘  │   ○ step 3       │
│               │  [provider ▾][model ▾][⟳]    │  🦑 Timeline     │
│ 🌙 theme      │  ┌────────────────────────┐  │   🐚 shell  done │
│ ⚙️ settings   │  │ 📎  type a message...  ▶ │  │   🔍 search ...  │
└───────────────┴──────────────────────────────┴──────────────────┘
```

- **Sidebar (left)** — new chat, conversation search, conversation list (click to open, double-click title to rename, trash icon to delete), theme toggle, settings, Google sign-in.
- **Chat (center)** — streaming messages with Markdown, inline tool cards, the message box (with file-upload 📎 and Stop ⏹).
- **Header** — chat title, **model switcher** (provider + model + ⟳ refresh local models), activity-panel toggle, export.
- **Agent Activity (right)** — live **Plan** checklist and a **Tentacle Timeline** of tool calls. Toggle it from the header; it auto-opens when the agent plans or uses tools.

---

## 4. First-time setup (pick a model)

Open **⚙️ Settings** and choose **one** path:

### A) Cloud provider (OpenAI / Anthropic / Gemini)
1. Select the provider card.
2. Paste your API key under **API Keys** → **Save** (keys are stored in `.env`, never in `config.json`).
3. Pick a model in the header switcher.

### B) Gemini via Google Sign-In (no API key)
1. Add a Google OAuth **Client ID** under *Google Sign-In* → Save.
2. Click **Sign in with Google**. Octopus switches to Gemini automatically.

### C) Local & free (Ollama)
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2          # or any tool-capable model
```
In Settings select **Ollama**, set the base URL if non-default, then pick the model (the header switcher auto-discovers installed models with the ⟳ button).

### D) Local OpenAI-compatible (LM Studio / llama.cpp / vLLM)
1. Start your server (e.g. LM Studio's local server on `http://localhost:1234/v1`).
2. In Settings → **Local Runtimes**, set the **base URL**, optional **API key**, and **model name**.
3. Select the **Local** provider.

➡️ Full details and tradeoffs: **[Providers & Models](providers-and-models.md)**.

---

## 5. Settings reference (in-app)

| Setting | What it does |
| :-- | :-- |
| **LLM Provider** | OpenAI · Anthropic · Gemini · Ollama · Local |
| **Model** | The specific model (local/Ollama discovered live) |
| **Tool Mode** | `auto` (native tools when supported, else emulated) · `native` · `emulated` · `off` |
| **Temperature** | 0.0 (focused) → 1.0 (creative) |
| **Tentacle Permissions** | Enable/disable each tool: Shell, File, Web, Code, Search, Image, Plan, Delegate |
| **Local Runtimes** | Ollama base URL; Local base URL / API key / model |
| **API Keys** | OpenAI / Anthropic / Gemini keys (saved to `.env`) |
| **Custom System Prompt** | Override the default Octopus personality/instructions |
| **Google Sign-In** | OAuth client ID + sign in/out for Gemini |

See the full machine-level reference in **[Configuration](configuration.md)**.

---

## 6. Using Octopus

Just type. Octopus decides when to use tools. For multi-step requests it will usually **plan first** (watch the Agent Activity panel), then act.

### Example prompts

| Tentacle | Try |
| :-- | :-- |
| 🐚 Shell | "List the files in the workspace and show disk usage." |
| 📁 Files | "Create `notes.md` with a project outline, then read it back." |
| 🔍 Search | "Search the web for the latest on WebGPU." |
| 💻 Code | "Write and run a Python script that computes the first 20 primes." |
| 🌐 Web | "Open news.ycombinator.com and summarize the top 5 stories." |
| 🎨 Image | "Generate an image of a cyberpunk octopus in neon lights." |
| 🗺️ Plan | "Plan and build a small CLI to-do app, then implement it." |
| 🤝 Delegate | "Research three vector databases, delegate the comparison, and summarize." |

### Controls
- **Send** — Enter. **Newline** — Shift+Enter.
- **Stop** — the ⏹ button truly interrupts a running response.
- **Attach a file** — 📎 uploads it (≤10 MB) and references it for analysis.
- **Rename** — double-click a conversation title. **Delete** — trash icon.
- **Export** — the export button downloads the chat as Markdown (JSON also available via the API).

### Keyboard shortcuts
| Shortcut | Action |
| :-- | :-- |
| `Ctrl/Cmd + N` | New chat |
| `Ctrl/Cmd + K` | Focus conversation search |
| `Esc` | Close modals / mobile sidebar |

---

## 7. How tools appear

When Octopus uses a tentacle you'll see:
1. An **inline tool card** in the chat (arguments + result, collapsible).
2. An entry in the **Tentacle Timeline** (running → done/failed).
3. For planning, a live checklist in the **Plan** section.

All external/tool content is treated as untrusted data — Octopus won't follow instructions hidden inside web pages or tool output. See **[Security](security.md)**.

---

## 8. Troubleshooting

| Symptom | Fix |
| :-- | :-- |
| UI loads but "Failed to connect to backend" | Backend isn't running on `:8000`. Start it (`./start.sh` or uvicorn). |
| "API key not configured" | Add a key in Settings, or switch to Ollama/Local. |
| Ollama models don't appear | Ensure `ollama serve` is running and the base URL is correct, then click ⟳. |
| Local model errors on tool use | Some small models can't do native tools — set **Tool Mode → emulated**. |
| Web Browse fails | Install the browser: `playwright install chromium`. |
| Shell command "blocked" | It matched the destructive-command denylist (see [Security](security.md)). |
| File op "outside the restricted workspace" | File/Shell are jailed to `data/workspace` (configurable via `OCTOPUS_WORKSPACE_DIR`). |
| `python-multipart` import error | `pip install -r backend/requirements.txt` (it's required for uploads). |
| Port already in use | Change the port in `start.sh` / uvicorn, or stop the other process. |

> More backend detail (API docs at `http://localhost:8000/docs`) and internals are in the [Developer docs](README.md#for-developers).
