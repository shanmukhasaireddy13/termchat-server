from termchat.config import (
    DEFAULT_FALLBACK_SERVER,
    FALLBACK_DEFAULT_SERVER,
    PRIMARY_DEFAULT_SERVER,
    get_default_servers,
    get_saved_server_url,
    normalize_urls,
)


def test_get_saved_server_url_default(monkeypatch):
    monkeypatch.delenv("TERMCHAT_SERVER", raising=False)
    monkeypatch.setattr("termchat.config.load_config", lambda: {})
    primary, fallback = get_default_servers()
    assert primary == PRIMARY_DEFAULT_SERVER
    assert "termchat.cliy.me" in primary
    assert fallback == FALLBACK_DEFAULT_SERVER
    assert "termchat-live.onrender.com" in fallback
    assert get_saved_server_url() == PRIMARY_DEFAULT_SERVER


def test_normalize_urls_https():
    ws_url, http_base = normalize_urls("https://my-app.onrender.com")
    assert ws_url == "wss://my-app.onrender.com/ws"
    assert http_base == "https://my-app.onrender.com"


def test_normalize_urls_http():
    ws_url, http_base = normalize_urls("http://localhost:8000")
    assert ws_url == "ws://localhost:8000/ws"
    assert http_base == "http://localhost:8000"


def test_normalize_urls_bare():
    ws_url, http_base = normalize_urls("my-app.onrender.com")
    assert ws_url == "wss://my-app.onrender.com/ws"
    assert http_base == "https://my-app.onrender.com"


def test_normalize_urls_with_trailing_slash_or_ws():
    ws_url, http_base = normalize_urls("https://chat.example.com/ws/")
    assert ws_url == "wss://chat.example.com/ws"
    assert http_base == "https://chat.example.com"
