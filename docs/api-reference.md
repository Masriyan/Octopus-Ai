# 🔌 API Reference

The backend's HTTP + WebSocket surface. Base URL: `http://localhost:8000`.

> Interactive docs (Swagger UI): **http://localhost:8000/docs**
> 📎 Related: [Architecture](architecture.md) · [Agent Engine](agent-engine.md)

> ⚠️ **Localhost-only.** All endpoints reject non-`127.0.0.1`/`::1` clients (`LocalhostRestrictionMiddleware`) and are rate-limited (120 req/min/IP). There is no auth token — do not expose this port publicly. See [Security](security.md).

---

## REST endpoints

### Health & tools
| Method | Path | Description |
| :-- | :-- | :-- |
| `GET` | `/api/health` | `{status, agent, version, tools}` |
| `GET` | `/api/tools` | List registered tentacles `[{name, description}]` |

### Conversations
| Method | Path | Description |
| :-- | :-- | :-- |
| `GET` | `/api/conversations` | List (id, title, updated_at, message_count) |
| `POST` | `/api/conversations` | Create; returns the new conversation |
| `GET` | `/api/conversations/{id}` | Full conversation with messages |
| `PATCH` | `/api/conversations/{id}` | Rename — body `{"title": "..."}` |
| `DELETE` | `/api/conversations/{id}` | Delete |
| `GET` | `/api/conversations/{id}/export?format=json\|markdown` | Download export |

### Configuration
| Method | Path | Description |
| :-- | :-- | :-- |
| `GET` | `/api/config` | Effective config (**API keys masked**) |
| `POST` | `/api/config` | Merge-update config — body = partial config |
| `POST` | `/api/config/apikey` | Save a key — `{"provider","key"}` (openai/anthropic/gemini) |
| `GET` | `/api/config/system-prompt` | `{system_prompt}` |
| `POST` | `/api/config/system-prompt` | `{system_prompt}` |
| `POST` | `/api/config/google-client-id` | `{client_id}` |

### Models
| Method | Path | Description |
| :-- | :-- | :-- |
| `GET` | `/api/models/{provider}` | List models. `ollama`/`local` are queried live; others return a static list. |

### Google OAuth (for Gemini)
| Method | Path | Description |
| :-- | :-- | :-- |
| `POST` | `/api/auth/google` | Store an OAuth token — `{access_token, name, email}` |
| `GET` | `/api/auth/google/status` | `{authenticated, user_name, user_email}` |
| `POST` | `/api/auth/google/signout` | Clear the session |

### Files
| Method | Path | Description |
| :-- | :-- | :-- |
| `POST` | `/api/upload` | multipart file upload (≤ 10 MB) → saved under `data/uploads/` |

---

## WebSocket protocol

Endpoint: `ws://localhost:8000/ws/chat/{conv_id}` (the conversation must already exist, else the socket closes with code `1008`).

### Client → server
```jsonc
{ "content": "your message" }     // send a user message
{ "type": "stop" }                // cancel the in-flight response
```
- Sending a new message while one is still streaming is rejected with an `error` event ("Still processing the previous message.").

### Server → client (event stream)
Each frame is one JSON object with a `type`:

| `type` | Fields | Meaning |
| :-- | :-- | :-- |
| `text` | `content` | a streamed token chunk (append to the current message) |
| `tool_start` | `tool`, `arguments`, `id` | a tentacle began |
| `tool_result` | `tool`, `result`, `id` | a tentacle finished (`result.status` = success/error/…) |
| `plan` | `steps: [{title, status}]` | the live plan checklist changed |
| `error` | `content` | a recoverable error message |
| `done` | `content` | the turn ended (also sent after `stop`) |

### Example exchange
```text
→ { "content": "list the files and plan it" }
← { "type": "text", "content": "Planning. " }
← { "type": "tool_start", "tool": "update_plan", "id": "pl", "arguments": {…} }
← { "type": "tool_start", "tool": "file_operations", "id": "fo", "arguments": {…} }
← { "type": "tool_result", "tool": "update_plan", "id": "pl", "result": {…} }
← { "type": "plan", "steps": [ {"title":"list files","status":"in_progress"} ] }
← { "type": "tool_result", "tool": "file_operations", "id": "fo", "result": {…} }
← { "type": "text", "content": "Done — I listed the workspace." }
← { "type": "done", "content": "" }
```

---

## curl quickstart

```bash
# health
curl localhost:8000/api/health

# create a conversation
CID=$(curl -s -XPOST localhost:8000/api/conversations | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# list ollama models
curl localhost:8000/api/models/ollama

# set the provider/model
curl -XPOST localhost:8000/api/config -H 'Content-Type: application/json' \
  -d '{"llm_provider":"ollama","model":"llama3.2"}'
```

WebSocket is easiest from the browser UI, or a small Python client using `websockets`.
