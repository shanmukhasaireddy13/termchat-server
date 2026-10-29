"""
Configuration management for termchat client.
Handles persistent user preferences in ~/.termchat.json, environment variables,
and URL normalization for WebSocket and HTTP endpoints.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

CONFIG_FILE = Path.home() / ".termchat.json"
PRIMARY_DEFAULT_SERVER = "https://termchat.cliy.me"
FALLBACK_DEFAULT_SERVER = "https://termchat-live.onrender.com"
DEFAULT_FALLBACK_SERVER = FALLBACK_DEFAULT_SERVER



def load_config() -> Dict[str, str]:
    """Loads configuration from ~/.termchat.json if present."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: Dict[str, str]):
    """Persists configuration to ~/.termchat.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[Warning] Could not save config file: {e}")


def get_default_servers() -> Tuple[str, Optional[str]]:
    """
    Returns (primary_server, fallback_server).
    Defaults to the live cloud server (https://termchat.cliy.me) with Render fallback.
    Ignores stale local entries (localhost/127.0.0.1) in ~/.termchat.json unless passed explicitly via CLI flag.
    """
    # 1. Environment variable takes highest priority
    env_url = os.environ.get("TERMCHAT_SERVER")
    if env_url:
        return env_url.strip(), PRIMARY_DEFAULT_SERVER

    # 2. Config file
    cfg = load_config()
    saved = cfg.get("server", "").strip() if cfg else ""
    # Filter out stale localhost entries from previous local debugging
    if saved and not any(h in saved.lower() for h in ("localhost", "127.0.0.1")):
        return saved, PRIMARY_DEFAULT_SERVER

    # 3. Default primary custom domain with Render fallback
    return PRIMARY_DEFAULT_SERVER, FALLBACK_DEFAULT_SERVER


def get_saved_server_url() -> str:
    """Retrieves server URL from ENV, config file, or falls back to PRIMARY_DEFAULT_SERVER."""
    primary, _ = get_default_servers()
    return primary


def set_saved_server_url(url: str):
    """Saves default server URL to config file."""
    cfg = load_config()
    cfg["server"] = url.strip()
    save_config(cfg)


def get_saved_username() -> str:
    """Retrieves saved username or falls back to system username."""
    cfg = load_config()
    if "username" in cfg and cfg["username"]:
        return cfg["username"].strip()
    return os.environ.get("USER") or os.environ.get("USERNAME") or "TermUser"


def set_saved_username(username: str):
    """Saves default username to config file."""
    cfg = load_config()
    cfg["username"] = username.strip()
    save_config(cfg)


def get_saved_ai_key() -> Optional[str]:
    """Retrieves saved AI key."""
    env_key = os.environ.get("AI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("KILO_API_KEY")
    if env_key:
        return env_key.strip()
    cfg = load_config()
    return cfg.get("ai_key")


def set_saved_ai_key(key: str):
    """Saves AI key to config file."""
    cfg = load_config()
    cfg["ai_key"] = key.strip()
    save_config(cfg)



def normalize_urls(raw_url: str):
    """
    Given a user-provided URL (e.g. 'https://my-app.onrender.com' or 'localhost:8000'),
    returns (ws_url, http_base_url).
    """
    cleaned = raw_url.strip()
    if not cleaned:
        cleaned = DEFAULT_FALLBACK_SERVER

    # Ensure protocol
    if not cleaned.startswith("http://") and not cleaned.startswith("https://") and not cleaned.startswith("ws://") and not cleaned.startswith("wss://"):
        if "localhost" in cleaned or "127.0.0.1" in cleaned:
            cleaned = f"http://{cleaned}"
        else:
            cleaned = f"https://{cleaned}"

    # Determine HTTP and WS protocols
    if cleaned.startswith("https://"):
        http_base = cleaned.rstrip("/")
        ws_base = "wss://" + cleaned[8:].rstrip("/")
    elif cleaned.startswith("http://"):
        http_base = cleaned.rstrip("/")
        ws_base = "ws://" + cleaned[7:].rstrip("/")
    elif cleaned.startswith("wss://"):
        http_base = "https://" + cleaned[6:].rstrip("/")
        ws_base = cleaned.rstrip("/")
    elif cleaned.startswith("ws://"):
        http_base = "http://" + cleaned[5:].rstrip("/")
        ws_base = cleaned.rstrip("/")
    else:
        http_base = f"https://{cleaned.rstrip('/')}"
        ws_base = f"wss://{cleaned.rstrip('/')}"

    # Strip /ws or trailing slashes from base
    if http_base.endswith("/ws"):
        http_base = http_base[:-3]
    if ws_base.endswith("/ws"):
        ws_base = ws_base[:-3]

    ws_url = f"{ws_base}/ws"
    return ws_url, http_base
