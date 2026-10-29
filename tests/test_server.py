import io
import json
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from server.main import app, manager


@pytest.fixture(autouse=True)
def reset_server_state():
    manager.active_connections.clear()
    manager.history.clear()
    yield


def test_server_status_and_static():
    client = TestClient(app)
    # Check index.html
    r = client.get("/")
    assert r.status_code == 200
    assert "termchat" in r.text

    # Check /health and /api/health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    r_api_health = client.get("/api/health")
    assert r_api_health.status_code == 200
    assert r_api_health.json()["status"] == "healthy"

    # Check /api/status
    r_status = client.get("/api/status")
    assert r_status.status_code == 200
    assert r_status.json()["status"] == "online"


def test_websocket_and_image_upload():
    client = TestClient(app)

    # Connect terminal client
    with client.websocket_connect("/ws?username=TerminalUser&client_type=terminal") as ws_term:
        # Message 1: history
        h = json.loads(ws_term.receive_text())
        assert h["type"] == "history"

        # Message 2: join announcement
        j = json.loads(ws_term.receive_text())
        assert j["type"] == "system"
        assert "TerminalUser joined" in j["text"]

        # Message 3: user_list
        u = json.loads(ws_term.receive_text())
        assert u["type"] == "user_list"

        # Terminal sends chat message
        ws_term.send_text(json.dumps({"type": "chat", "text": "Hello from terminal"}))
        echo = json.loads(ws_term.receive_text())
        assert echo["type"] == "chat"
        assert echo["sender"] == "TerminalUser"
        assert echo["text"] == "Hello from terminal"

        # Now simulate web client uploading an image via POST /api/upload
        img_bytes = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="red")
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = client.post(
            "/api/upload",
            files={"file": ("screenshot.png", img_bytes, "image/png")},
            data={"sender": "WebMaster", "client_type": "web"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        image_url = response.json()["url"]
        assert image_url.startswith("/uploads/")

        # The terminal client should have received the broadcast image message!
        img_msg = json.loads(ws_term.receive_text())
        assert img_msg["type"] == "image"
        assert img_msg["sender"] == "WebMaster"
        assert img_msg["client_type"] == "web"
        assert img_msg["image_url"] == image_url
