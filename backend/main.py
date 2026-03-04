"""
Octopus AI — Main Server 🐙
FastAPI application with WebSocket for real-time chat and REST endpoints.
"""
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from config import get_config, update_config, save_config
from memory import MemoryManager
from agent import agent
from tools import registry, register_all_tools
from llm_providers import OllamaProvider

app = FastAPI(
    title="Octopus AI",
    description="🐙 Multi-capability AI agent with many tentacles",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = MemoryManager()

# ─── WebSocket Chat Endpoint ──────────────────────────────────────────────

@app.websocket("/ws/chat/{conv_id}")
async def websocket_chat(websocket: WebSocket, conv_id: str):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_text = message.get("content", "")

            if not user_text.strip():
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            # Stream response from agent
            async for event in agent.process_message(conv_id, user_text):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass


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
        ollama = OllamaProvider()
        models = await ollama.list_models()
        return {"models": models}
    elif provider == "openai":
        return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}
    elif provider == "anthropic":
        return {"models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]}
    elif provider == "gemini":
        return {"models": ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash", "gemini-2.5-pro"]}
    return {"models": []}


# Health
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "agent": "Octopus AI 🐙",
        "version": "1.0.0"
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
