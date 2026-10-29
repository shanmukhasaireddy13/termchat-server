import subprocess
import sys
from termchat import __version__


def test_cli_version():
    res = subprocess.run([sys.executable, "-m", "termchat", "--version"], capture_output=True, text=True)
    assert res.returncode == 0
    assert __version__ in res.stdout or __version__ in res.stderr


def test_cli_help():
    res = subprocess.run([sys.executable, "-m", "termchat", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "termchat" in res.stdout


def test_client_badge_format_no_globe_icon(capsys):
    from termchat.client import TerminalClient
    client = TerminalClient(server_url="https://test.example.com", username="tester")
    
    # Test chat badge
    client.handle_incoming_chat({"sender": "Alice", "client_type": "web", "text": "hello"})
    captured = capsys.readouterr().out
    assert "[Web] Alice: hello" in captured
    assert "🌐" not in captured

    # Test image badge
    client.handle_incoming_image({"sender": "Alice", "client_type": "web", "image_url": "/test.png", "filename": "test.png"})
    captured_img = capsys.readouterr().out
    assert "[Web] Alice Sent an image: test.png" in captured_img
    assert "🌐" not in captured_img


def test_ai_query_handling_offline(capsys, monkeypatch):
    from termchat.client import TerminalClient
    client = TerminalClient(server_url="https://test.example.com", username="tester")
    monkeypatch.setattr("termchat.client.query_llm", lambda q, **kwargs: f"Answer: {q}")
    
    # Offline query should call handle_incoming_ai directly
    client.handle_incoming_ai({"sender": "🤖 TermChat AI", "text": "Answer: 42"})
    out = capsys.readouterr().out
    assert "TermChat AI" in out
    assert "Answer: 42" in out
