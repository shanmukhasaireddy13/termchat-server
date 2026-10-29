"""
termchat Online Server (Render / Cloud deployable).
Coordinates real-time bi-directional messaging between Terminal CLI clients and Web UI clients.
Supports text messaging, image uploads, clipboard pasting, and WebSocket broadcasting.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, File, Form, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("termchat.server")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit


class ConnectionManager:
    def __init__(self, max_history: int = 100):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        username: str,
        client_type: str,
        device_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        await websocket.accept()
        session = {
            "websocket": websocket,
            "username": username.strip() or "Anonymous",
            "client_type": client_type,
            "device_info": device_info or "Unknown",
            "id": str(uuid.uuid4())[:8],
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            self.active_connections[websocket] = session

        logger.info(f"Connected: {session['username']} [{client_type}]")

        # Send existing history to the client
        await self.send_personal(websocket, {"type": "history", "messages": self.history})

        # Broadcast join notification
        join_msg = {
            "id": str(uuid.uuid4()),
            "type": "system",
            "sender": "System",
            "text": f"{session['username']} joined via {client_type.upper()}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.add_history(join_msg)
        await self.broadcast(join_msg)
        await self.broadcast_user_list()
        return session

    async def disconnect(self, websocket: WebSocket):
        session = None
        async with self._lock:
            if websocket in self.active_connections:
                session = self.active_connections.pop(websocket)

        if session:
            logger.info(f"Disconnected: {session['username']}")
            leave_msg = {
                "id": str(uuid.uuid4()),
                "type": "system",
                "sender": "System",
                "text": f"{session['username']} left the chat.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.add_history(leave_msg)
            await self.broadcast(leave_msg)
            await self.broadcast_user_list()

    def add_history(self, msg: Dict[str, Any]):
        if msg.get("type") in ("chat", "image", "system"):
            self.history.append(msg)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

    def get_users(self) -> List[Dict[str, Any]]:
        return [
            {
                "username": s["username"],
                "client_type": s["client_type"],
                "device_info": s["device_info"],
            }
            for s in self.active_connections.values()
        ]

    async def broadcast_user_list(self):
        payload = {
            "type": "user_list",
            "users": self.get_users(),
            "count": len(self.active_connections),
        }
        await self.broadcast(payload)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.debug(f"Error sending personal: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        dead = []
        for ws in list(self.active_connections.keys()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)


from server.ai import query_llm

manager = ConnectionManager()


from contextlib import asynccontextmanager

# Heartbeat task for Render / Cloud deployment (keeps websockets alive)
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def heartbeat():
        while True:
            await asyncio.sleep(25)
            if manager.active_connections:
                await manager.broadcast({"type": "ping"})

    task = asyncio.create_task(heartbeat())
    yield
    task.cancel()


app = FastAPI(title="termchat Online Server", version="1.0.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and uploads mounting
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "termchat server is running"}


@app.get("/api/status")
async def status():
    return {
        "status": "online",
        "active_clients": len(manager.active_connections),
        "users": manager.get_users(),
    }


@app.get("/api/history")
async def history():
    return {"history": manager.history}


@app.post("/api/ai")
async def ask_ai_endpoint(payload: dict):
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return {"error": "Prompt is required"}
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(None, query_llm, prompt, manager.history)
    return {"prompt": prompt, "answer": answer}



@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    sender: str = Form(default="WebUser"),
    client_type: str = Form(default="web"),
):
    """
    Handles image uploads from the web client (drag & drop, picker, or clipboard paste).
    Saves image and broadcasts an image message to all connected clients including the terminal.
    """
    ext = Path(file.filename or "image.png").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".png"

    unique_filename = f"{uuid.uuid4().hex[:12]}_{Path(file.filename or 'upload').stem[:16]}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    # Save to disk
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_rel_url = f"/uploads/{unique_filename}"

    # Broadcast image message to all clients
    image_msg = {
        "id": str(uuid.uuid4()),
        "type": "image",
        "sender": sender.strip() or "WebUser",
        "client_type": client_type,
        "image_url": image_rel_url,
        "filename": file.filename or "image.png",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    manager.add_history(image_msg)
    await manager.broadcast(image_msg)

    return {"status": "ok", "url": image_rel_url, "message": image_msg}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    username: str = Query(default="Anonymous"),
    client_type: str = Query(default="terminal"),
    device_info: Optional[str] = Query(default=None),
):
    session = await manager.connect(websocket, username, client_type, device_info)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                data = {"type": "chat", "text": raw_text}

            m_type = data.get("type", "chat")

            if m_type == "chat":
                text = (data.get("text") or "").strip()
                if not text:
                    continue

                # Check if this is an AI query
                is_ai_query = (
                    text.startswith("/ai ")
                    or text.startswith("@ai ")
                    or text.startswith("/ask ")
                    or text.startswith("ai: ")
                )

                if is_ai_query:
                    # Extract prompt
                    if text.startswith("/ai ") or text.startswith("@ai "):
                        prompt = text[4:].strip()
                    else:
                        prompt = text.split(" ", 1)[1].strip()

                    # 1. Broadcast user's query
                    user_msg = {
                        "id": str(uuid.uuid4()),
                        "type": "chat",
                        "sender": session["username"],
                        "client_type": session["client_type"],
                        "text": text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "device_info": session["device_info"],
                    }
                    manager.add_history(user_msg)
                    await manager.broadcast(user_msg)

                    # 2. Query AI asynchronously
                    loop = asyncio.get_running_loop()
                    answer = await loop.run_in_executor(None, query_llm, prompt, manager.history)

                    # 3. Broadcast AI response
                    ai_msg = {
                        "id": str(uuid.uuid4()),
                        "type": "ai",
                        "sender": "🤖 TermChat AI",
                        "client_type": "ai",
                        "text": answer,
                        "prompt": prompt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    manager.add_history(ai_msg)
                    await manager.broadcast(ai_msg)
                    continue

                chat_msg = {
                    "id": str(uuid.uuid4()),
                    "type": "chat",
                    "sender": session["username"],
                    "client_type": session["client_type"],
                    "text": text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "device_info": session["device_info"],
                }
                manager.add_history(chat_msg)
                await manager.broadcast(chat_msg)


            elif m_type == "pong":
                continue

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WS error: {e}")
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
