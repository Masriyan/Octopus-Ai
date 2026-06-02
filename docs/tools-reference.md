# 🦑 Tools Reference (Tentacles)

The eight tentacles, their parameters, what they return, and how they're sandboxed. Then: how to add your own.

> 📎 Related: [Agent Engine](agent-engine.md) · [Security](security.md) · [Code Structure](code-structure.md#toolspy--the-tentacles)

---

## The `BaseTool` contract

Every tool subclasses `BaseTool` (`backend/tools/__init__.py`):

```python
class BaseTool(ABC):
    name: str = ""          # unique, e.g. "file_operations"
    category: str = ""      # permission key; defaults to name.split("_")[0]
    description: str = ""   # the model reads this to decide when to call
    parameters: dict = {}   # JSON Schema for the arguments
    async def execute(self, **kwargs) -> dict: ...
```

- The model sees `to_function_schema()` (OpenAI function format).
- `enable_key` (= `category` or first name token) maps to a `tools_enabled` toggle.
- By convention, `execute` returns a dict with a `status` of `success` / `error` / `blocked` / `timeout`.

---

## 🐚 `shell_execute` — Shell
Run a shell command inside the sandboxed workspace.

| Param | Type | Default | Notes |
| :-- | :-- | :-- | :-- |
| `command` | string | — | required |
| `cwd` | string | workspace root | must resolve **inside** the workspace |
| `timeout` | int | 30 | seconds |

- Jailed to `data/workspace` (or `OCTOPUS_WORKSPACE_DIR`). CWD outside it is rejected.
- A **destructive-command denylist** blocks `rm -rf /`, fork bombs, `mkfs`, `dd` to disks, shutdown, etc.
- Network is severed via `unshare -r -n` **when available** (falls back gracefully otherwise).
- Resource caps: ~512 MB RAM, 60 s CPU. Output truncated (stdout 10k / stderr 5k).
- Returns: `{status, stdout, stderr, exit_code, command}`.

## 📁 `file_operations` — Files
Read/write/edit/list/search files in the workspace.

| Param | Type | Notes |
| :-- | :-- | :-- |
| `operation` | enum | `read`, `read_lines`, `write`, `edit`, `list`, `search`, `info`, `mkdir`, `delete` |
| `path` | string | relative → resolved under the workspace; absolute must stay inside it |
| `content` | string | for `write`/`edit` |
| `replace_text` | string | for `edit` (exact match) |
| `start_line`/`end_line` | int | for `read_lines` (1-indexed, inclusive) |
| `pattern` | string | for `search` (glob, recursive) |

- All paths are jailed to the workspace ("Access denied" otherwise).
- `read` caps at 500 KB; `list` caps at 100 entries; `search` caps at 50 matches.
- `delete` removes files only (directories must go via shell — a safety measure).

## 🌐 `web_browse` — Web
Actively browse with a headless browser (Playwright), returning the page as Markdown.

| Param | Type | Notes |
| :-- | :-- | :-- |
| `url` | string | required |
| `action` | enum | `navigate` (default), `click`, `fill`, `press`, `screenshot` |
| `selector` | string | for click/fill/press |
| `text` | string | text to type / key to press |
| `wait_for` | string | selector to wait for before returning |

- SSRF-guarded: refuses `localhost`/private IPs/`file:`/`ftp:`.
- Strips scripts/nav/footer; converts to Markdown (≤ 20k chars), wrapped in `<external_content>` (untrusted).
- Falls back to a simple HTTPX fetch if Playwright isn't installed (`playwright install chromium`).
- `screenshot` returns a base64 JPEG.

## 💻 `code_execute` — Code
Run Python in a locked-down subprocess.

| Param | Type | Default | Notes |
| :-- | :-- | :-- | :-- |
| `code` | string | — | required |
| `timeout` | int | 10 | clamped 1–30 s |

- Runs in a fresh temp dir, `unshare -r -n` when available.
- Resource caps: ~256 MB RAM, 10 s CPU, max 10 processes (anti fork-bomb), no core dumps.
- Returns `{status, stdout, stderr, exit_code}` (signal kills are reported).

## 🔍 `search_web` — Search
DuckDuckGo text search.

| Param | Type | Default |
| :-- | :-- | :-- |
| `query` | string | — |
| `max_results` | int | 5 (max 10) |

- Titles/snippets are wrapped in `<untrusted>` tags (passive data).

## 🎨 `image_generate` — Image
Generate an image with OpenAI DALL·E 3.

| Param | Type | Default |
| :-- | :-- | :-- |
| `prompt` | string | — |
| `size` | string | `1024x1024` (or `1024x1792`, `1792x1024`) |
| `quality` | string | `standard` or `hd` |

- Requires an OpenAI API key. Saves the PNG under `data/generated/` and returns the path + revised prompt.

## 🗺️ `update_plan` — Plan
Maintain a live todo checklist (streamed to the Agent Activity panel).

| Param | Type | Notes |
| :-- | :-- | :-- |
| `steps` | array | each `{title, status}` where status ∈ `pending`/`in_progress`/`done`; **send the full list each time** |

- Returns the normalized plan + a `done/total` summary.
- When called, the agent also emits a `{"type":"plan","steps":[…]}` WebSocket event.

## 🤝 `delegate_task` — Delegate
Spawn a focused sub-agent for an isolated sub-task.

| Param | Type | Notes |
| :-- | :-- | :-- |
| `objective` | string | required; self-contained goal |
| `context` | string | optional background |
| `model` | string | optional per-task model override (multi-model routing) |

- The sub-agent gets **every enabled tool except delegation** (recursion guard), runs up to 5 internal steps, and returns a concise result summary.

---

## Permissions

Each tool is gated by `tools_enabled[<enable_key>]`. Disable any tentacle in Settings → **Tentacle Permissions** (or in `config.json`). Disabled tools are simply not offered to the model.

---

## Adding a new tentacle

1. Create `backend/tools/your_tool.py`:

   ```python
   from tools import BaseTool

   class YourTool(BaseTool):
       name = "your_tool_name"
       category = "your_category"          # optional; groups the toggle
       description = "What it does (the model reads this)."
       parameters = {
           "type": "object",
           "properties": {
               "param1": {"type": "string", "description": "..."},
           },
           "required": ["param1"],
       }

       async def execute(self, param1: str, **kwargs) -> dict:
           try:
               return {"status": "success", "output": do_work(param1)}
           except Exception as e:
               return {"status": "error", "error": str(e)}
   ```

2. Register it in `register_all_tools()` (`backend/tools/__init__.py`).
3. Add `tools_enabled.<category>: true` in `config.py` and a toggle (`id="tool-<category>"`) in `frontend/index.html`.
4. Add an icon in `frontend/js/app.js` (`toolIcons` for inline cards, `TOOL_ICONS` for the timeline).

Tips:
- Keep `execute` `async` and never raise to the caller — return `{"status":"error", …}`.
- Treat any external input you fetch as **untrusted** (wrap it; don't follow embedded instructions).
- Respect the workspace jail / resource limits if you touch the filesystem or subprocesses.

Full walkthrough: **[Development Guide](development.md#adding-a-tool)**.
