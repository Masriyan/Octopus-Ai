# 🛠️ Development Guide

Set up a dev environment, run tests, follow the conventions, and extend Octopus (new tools & providers).

> 📎 Related: [Code Structure](code-structure.md) · [Tools Reference](tools-reference.md) · [Providers & Models](providers-and-models.md)

---

## Dev setup

```bash
git clone https://github.com/Masriyan/Octopus-Ai.git
cd Octopus-Ai
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium            # for the Web Browse tentacle

cp .env.example .env                   # add keys (optional)
```

Run the two tiers separately for hot-reload:

```bash
# backend (auto-reload)
cd backend && python3 -m uvicorn main:app --reload --port 8000

# frontend (static)
cd frontend && python3 -m http.server 5500
```

- Backend API docs: `http://localhost:8000/docs`.
- The frontend is a **module** script — serve it over HTTP (don't open `index.html` via `file://`, ES modules are blocked there).

---

## Testing

```bash
cd backend
pytest tests/ -q
```

The suite covers the file tool, memory, and web tool. An autouse fixture in `conftest.py` points `OCTOPUS_WORKSPACE_DIR` at each test's `tmp_path`, so File/Shell tests stay inside the sandbox.

### Testing the app without a real model
Monkeypatch the provider factory with a fake that yields the streaming event dicts:

```python
import agent as agent_mod
class Fake:
    supports_native_tools = True
    async def chat_stream(self, messages, tools=None, model=None, temperature=0.7):
        yield {"type": "text", "content": "hi"}
        yield {"type": "done"}
    async def chat(self, *a, **k): return {"type": "text", "content": "", "tool_calls": []}
agent_mod.get_provider = lambda name, cfg: Fake()
```

You can then drive `agent.process_message(...)` directly, or hit the whole app (including the WebSocket) with FastAPI's `TestClient`:

```python
from fastapi.testclient import TestClient
import main
with TestClient(main.app) as c:
    cid = c.post("/api/conversations").json()["id"]
    with c.websocket_connect(f"/ws/chat/{cid}") as ws:
        ws.send_json({"content": "hi"})
        # drain events until {"type":"done"}
```

> ⚡ Tip: importing the backend pulls in `sentence-transformers`/`torch` (heavy). For fast unit tests that don't need RAG, stub them before import:
> ```python
> import sys
> for m in ("sentence_transformers","qdrant_client","qdrant_client.models","torch"):
>     sys.modules[m] = None
> ```
> This makes `VectorMemory.enabled = False` (RAG no-ops) and the app boots instantly.

---

## Conventions

### Python (backend)
- PEP 8, type hints on signatures, docstrings on classes/public functions.
- `async`/`await` for all I/O. Tools must be `async` and **return** errors as `{"status":"error", …}` (never raise to the agent).
- Keep functions focused; prefer small helpers.
- Treat any external/tool content as **untrusted** — wrap it and never let it act as instructions.

### JavaScript (frontend)
- Vanilla JS, no frameworks, no build step.
- `const`/`let` only; small descriptive functions; comment non-obvious logic.
- Render model/tool output through `renderMarkdown` (which sanitizes via DOMPurify) — never `innerHTML` raw model text.

### Git
- One logical change per commit; clear messages; focused PRs.
- `data/`, `.env`, `venv/`, caches are git-ignored — never commit secrets or runtime data.

---

## Adding a tool

1. `backend/tools/your_tool.py` — subclass `BaseTool`, implement `async execute`. (Pattern in [Tools Reference](tools-reference.md#adding-a-new-tentacle).)
2. Import + add it in `register_all_tools()` (`backend/tools/__init__.py`).
3. Default toggle: add `tools_enabled.<category>: true` in `config.py`.
4. UI: add a checkbox `id="tool-<category>"` in `frontend/index.html` (Tentacle Permissions), and an icon in `app.js` (`toolIcons` + `TOOL_ICONS`).
5. Test it: instantiate and `await tool.execute(...)`.

## Adding a provider

1. `backend/llm_providers.py` — subclass `BaseLLMProvider`; implement `chat_stream` + `chat`; set `supports_native_tools`. Convert the canonical OpenAI-style messages to your API (reuse the Anthropic/Gemini converters as references).
2. Add a branch in `get_provider(name, config)`.
3. (Optional) `list_models()` + a case in `GET /api/models/{provider}`.
4. UI: add the provider to the header `<select>` and the settings provider cards, and handle it in `getModelsFor` (`frontend/js/app.js`).
5. Config: add any new keys (e.g. a `base_url`) to `DEFAULT_CONFIG` and `.env.example`.

## Adding a REST/WS endpoint
Add it to `backend/main.py`. It will automatically be localhost-restricted and rate-limited. Keep responses JSON-serializable.

---

## Project scripts

| Script | Purpose |
| :-- | :-- |
| `start.sh` | venv + deps + run backend (8000) and frontend (5500) |
| `backend/run_e2e.sh`, `backend/run_swarm_e2e.sh` | end-to-end helpers |
| `backend/test_playwright.py` | Playwright smoke check |

---

## Where things live (quick map)

| To change… | Edit |
| :-- | :-- |
| The agent loop / planning / emulation | `backend/agent.py` |
| A model integration | `backend/llm_providers.py` |
| A tool's behavior | `backend/tools/<tool>.py` |
| Config defaults/keys | `backend/config.py`, `.env.example` |
| The UI markup | `frontend/index.html` |
| The UI logic | `frontend/js/app.js` |
| The look | `frontend/css/main.css` |

See **[Code Structure](code-structure.md)** for the full map.
