"""
Octopus AI — Configuration Manager
Handles API keys, model preferences, and tool permissions.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
CONFIG_FILE = DATA_DIR / "config.json"
DOTENV_FILE = BASE_DIR / ".env"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "llm_provider": "openai",
    "model": "gpt-4o-mini",
    "api_keys": {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
    },
    "google_oauth": {
        "access_token": "",
        "user_name": "",
        "user_email": "",
        "authenticated": False,
    },
    "google_client_id": "",
    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    # OpenAI-compatible local server (LM Studio / llama.cpp / vLLM / ...)
    "local_openai_base_url": os.getenv("LOCAL_OPENAI_BASE_URL", "http://localhost:1234/v1"),
    "local_openai_api_key": os.getenv("LOCAL_OPENAI_API_KEY", ""),
    "local_openai_model": os.getenv("LOCAL_OPENAI_MODEL", ""),
    # How tools are driven: auto = native when supported else emulated;
    # native = require provider function-calling; emulated = always prompt-based;
    # off = no tools.
    "tool_mode": "auto",
    "tools_enabled": {
        "shell": True,
        "file": True,
        "web": True,
        "code": True,
        "search": True,
        "image": True,
        "plan": True,
        "delegate": True,
    },
    "max_context_messages": 50,
    "temperature": 0.7,
    "theme": "dark-ocean",
    "system_prompt": "",
}


def load_config() -> dict:
    """Load config from disk, merging with defaults."""
    merged = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            merged = {**merged, **saved}
            # Merge nested dicts (except api_keys which we pull from env)
            for key in ["tools_enabled"]:
                merged[key] = {**DEFAULT_CONFIG[key], **saved.get(key, {})}
        except (json.JSONDecodeError, IOError):
            pass
            
    # Always pull API keys fresh from environment
    merged["api_keys"] = {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
    }
    return merged


def save_config(config: dict):
    """Persist config to disk, but avoid saving sensitive credentials."""
    config_to_save = config.copy()
    
    # Pop API keys to save them to .env instead
    api_keys = config_to_save.pop("api_keys", {})
    if api_keys:
        import dotenv
        if not DOTENV_FILE.exists():
            DOTENV_FILE.touch()
        for provider, key in api_keys.items():
            if key:
                env_key = f"{provider.upper()}_API_KEY"
                dotenv.set_key(str(DOTENV_FILE), env_key, key)
                os.environ[env_key] = key

    # Mask Google OAuth access token to prevent long-lived persistent exfiltration
    if "google_oauth" in config_to_save:
        config_to_save["google_oauth"] = {
            "access_token": "",
            "user_name": config_to_save["google_oauth"].get("user_name", ""),
            "user_email": config_to_save["google_oauth"].get("user_email", ""),
            "authenticated": config_to_save["google_oauth"].get("authenticated", False),
        }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config_to_save, f, indent=2)


def get_data_dir() -> str:
    """Return the path to the data directory."""
    return str(DATA_DIR)


def get_workspace_dir() -> Path:
    """Return the sandboxed workspace root that File/Shell tools are jailed to.

    Configurable via the OCTOPUS_WORKSPACE_DIR env var (handy for tests or to
    point the agent at a project folder); defaults to ``data/workspace``.
    """
    override = os.getenv("OCTOPUS_WORKSPACE_DIR")
    base = Path(override).expanduser() if override else (DATA_DIR / "workspace")
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def get_config() -> dict:
    return load_config()


def update_config(updates: dict) -> dict:
    config = load_config()
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    save_config(config)
    return config
