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
    "tools_enabled": {
        "shell": True,
        "file": True,
        "web": True,
        "code": True,
        "search": True,
    },
    "max_context_messages": 50,
    "temperature": 0.7,
    "theme": "dark-ocean",
}


def load_config() -> dict:
    """Load config from disk, merging with defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            merged = {**DEFAULT_CONFIG, **saved}
            # Merge nested dicts
            for key in ["api_keys", "tools_enabled"]:
                merged[key] = {**DEFAULT_CONFIG[key], **saved.get(key, {})}
            return merged
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Persist config to disk."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


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
