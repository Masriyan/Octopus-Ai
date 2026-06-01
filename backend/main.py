"""
Octopus AI — Main Server 🐙
FastAPI application with WebSocket for real-time chat and REST endpoints.
"""
import json
import asyncio
import time
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import get_config, update_config, save_config, DATA_DIR
from agent import agent
from tools import registry, register_all_tools
from llm_providers import OllamaProvider, LocalOpenAIProvider

logger = logging.getLogger("octopus.server")

# ─── Rate Limiting Middleware ─────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory token bucket rate limiter."""
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Clean old entries
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < 60
        ]
        if len(self.requests[client_ip]) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
        self.requests[client_ip].append(now)
        return await call_next(request)


app = FastAPI(
    title="Octopus AI",
    description="🐙 Multi-capability AI agent with many tentacles",
    version="3.0.0",
)

# CORS for frontend. The backend already refuses non-local clients via
# LocalhostRestrictionMiddleware, so we can safely allow any localhost origin
# regardless of the dev port (5500 http.server, 5173 vite, 8000 self, etc.).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LocalhostRestrictionMiddleware(BaseHTTPMiddleware):
    """Restricts API access to localhost since there is no token auth yet."""
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        if client_ip not in ("127.0.0.1", "::1", "localhost", "testclient"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Access forbidden: External network access is blocked for security."},
            )
        return await call_next(request)

app.add_middleware(LocalhostRestrictionMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

# Reuse the agent's MemoryManager so we never open a second Qdrant client on
# the same local storage folder (embedded Qdrant allows only one per path).
memory = agent.memory


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Pre-register tools on startup."""
    register_all_tools()
    logger.info("🐙 Octopus AI started — tools registered")
    yield


app.router.lifespan_context = lifespan

# ─── WebSocket Chat Endpoint ──────────────────────────────────────────────

@app.websocket("/ws/chat/{conv_id}")
async def websocket_chat(websocket: WebSocket, conv_id: str):
    conv = memory.get_conversation(conv_id)
    if not conv:
        await websocket.close(code=1008, reason="Invalid conversation ID")
        return

    await websocket.accept()

    # The agent runs as a background task so we can keep listening for a
    # "stop" frame *while* a response is streaming (true cancellation).
    current_task: asyncio.Task | None = None
    cancel_event = asyncio.Event()

    async def run_agent(text: str, ev: asyncio.Event):
        try:
            # The agent yields its own terminal {"type": "done"} event, so we
            # simply forward events until it finishes or is cancelled.
            async for event in agent.process_message(conv_id, text, cancel_event=ev):
                if ev.is_set():
                    break
                await websocket.send_json(event)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Agent run failed")
            try:
                await websocket.send_json({"type": "error", "content": str(e)})
                await websocket.send_json({"type": "done", "content": ""})
            except Exception:
                pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Malformed message"})
                continue

            mtype = message.get("type")

            if mtype == "stop":
                cancel_event.set()
                if current_task and not current_task.done():
                    current_task.cancel()
                await websocket.send_json({"type": "done", "content": "Stopped by user"})
                continue

            user_text = message.get("content", "")
            if not user_text.strip():
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            if current_task and not current_task.done():
                await websocket.send_json({
                    "type": "error",
                    "content": "Still processing the previous message.",
                })
                continue

            cancel_event = asyncio.Event()
            current_task = asyncio.create_task(run_agent(user_text, cancel_event))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        cancel_event.set()
        if current_task and not current_task.done():
            current_task.cancel()


# ─── REST Endpoints ───────────────────────────────────────────────────────

# Conversations
@app.get("/api/conversations")
async def list_conversations():
    return {"conversations": memory.list_conversations()}


@app.post("/api/conversations")
async def create_conversation():
    conv = memory.create_conversation()
    return conv


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = memory.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    if memory.delete_conversation(conv_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")


@app.patch("/api/conversations/{conv_id}")
async def rename_conversation(conv_id: str, data: dict):
    title = data.get("title", "")
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    if memory.rename_conversation(conv_id, title):
        return {"status": "renamed", "title": title}
    raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/api/conversations/{conv_id}/export")
async def export_conversation(conv_id: str, format: str = "json"):
    result = memory.export_conversation(conv_id, format)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if format == "markdown":
        return PlainTextResponse(
            content=result,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="conversation_{conv_id}.md"'},
        )
    return PlainTextResponse(
        content=result,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="conversation_{conv_id}.json"'},
    )


# Configuration
@app.get("/api/config")
async def get_configuration():
    config = get_config()
    # Mask API keys for security
    safe_config = {**config}
    safe_keys = {}
    for provider, key in config.get("api_keys", {}).items():
        if key:
            safe_keys[provider] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        else:
            safe_keys[provider] = ""
    safe_config["api_keys"] = safe_keys
    return safe_config


@app.post("/api/config")
async def update_configuration(updates: dict):
    config = update_config(updates)
    return {"status": "updated"}


@app.post("/api/config/apikey")
async def set_api_key(data: dict):
    """Set an API key for a provider."""
    provider = data.get("provider", "")
    key = data.get("key", "")
    if provider not in ("openai", "anthropic", "gemini"):
        raise HTTPException(status_code=400, detail="Invalid provider")
    config = get_config()
    config["api_keys"][provider] = key
    save_config(config)
    return {"status": "saved", "provider": provider}


@app.post("/api/auth/google")
async def google_auth(data: dict):
    """Receive Google OAuth access token and store for Gemini API use."""
    access_token = data.get("access_token", "")
    user_name = data.get("name", "Google User")
    user_email = data.get("email", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided")

    # Store the OAuth token in config for GeminiProvider to use
    config = get_config()
    config["google_oauth"] = {
        "access_token": access_token,
        "user_name": user_name,
        "user_email": user_email,
        "authenticated": True,
    }
    # Auto-switch to Gemini provider when signing in with Google
    config["llm_provider"] = "gemini"
    save_config(config)

    return {
        "status": "authenticated",
        "provider": "gemini",
        "user_name": user_name,
    }


@app.post("/api/auth/google/signout")
async def google_signout():
    """Clear Google OAuth session."""
    config = get_config()
    config["google_oauth"] = {
        "access_token": "",
        "user_name": "",
        "user_email": "",
        "authenticated": False,
    }
    save_config(config)
    return {"status": "signed_out"}


@app.get("/api/auth/google/status")
async def google_auth_status():
    """Check if Google OAuth is active."""
    config = get_config()
    oauth = config.get("google_oauth", {})
    return {
        "authenticated": oauth.get("authenticated", False),
        "user_name": oauth.get("user_name", ""),
        "user_email": oauth.get("user_email", ""),
    }


@app.post("/api/config/google-client-id")
async def save_google_client_id(data: dict):
    """Save the Google OAuth Client ID."""
    client_id = data.get("client_id", "")
    config = get_config()
    config["google_client_id"] = client_id
    save_config(config)
    return {"status": "saved"}


# Tools
@app.get("/api/tools")
async def list_tools():
    register_all_tools()
    return {"tools": registry.list_tools()}


# Models
@app.get("/api/models/{provider}")
async def list_models(provider: str):
    if provider == "ollama":
        cfg = get_config()
        ollama = OllamaProvider(cfg.get("ollama_base_url", "http://localhost:11434"))
        models = await ollama.list_models()
        return {"models": models}
    elif provider == "local":
        cfg = get_config()
        local = LocalOpenAIProvider(
            base_url=cfg.get("local_openai_base_url", "http://localhost:1234/v1"),
            api_key=cfg.get("local_openai_api_key", "") or "not-needed",
        )
        models = await local.list_models()
        return {"models": models}
    elif provider == "openai":
        return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}
    elif provider == "anthropic":
        return {"models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]}
    elif provider == "gemini":
        return {"models": ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash", "gemini-2.5-pro"]}
    return {"models": []}


# System Prompt
@app.get("/api/config/system-prompt")
async def get_system_prompt():
    config = get_config()
    return {"system_prompt": config.get("system_prompt", "")}


@app.post("/api/config/system-prompt")
async def set_system_prompt(data: dict):
    prompt = data.get("system_prompt", "")
    config = get_config()
    config["system_prompt"] = prompt
    save_config(config)
    return {"status": "saved"}


# File Upload
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for the agent to process."""
    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / file.filename
    content = await file.read()

    # Limit file size to 10MB
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": str(file_path),
        "size": len(content),
    }


# Health
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "agent": "Octopus AI 🐙",
        "version": "3.0.0",
        "tools": len(registry._tools),
    }


# ─── Serve Frontend (Production) ─────────────────────────────────────────

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
