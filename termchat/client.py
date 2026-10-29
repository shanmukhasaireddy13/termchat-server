"""
Terminal Chat Client for termchat.
Non-intrusive standard terminal interface (no UI takeover, standard terminal stream).
Sends entered text to online Render/cloud server and displays incoming text and images.
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import sys
import urllib.parse
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import websockets

from termchat.config import normalize_urls
from termchat.viewer import download_image, open_system_image, render_ansi_thumbnail
from termchat.ai import query_llm



class TerminalClient:
    def __init__(
        self,
        server_url: str,
        username: str,
        fallback_url: Optional[str] = None,
        auto_open_images: bool = False,
        show_thumbnails: bool = True,
    ):
        self.username = username
        self.auto_open_images = auto_open_images
        self.show_thumbnails = show_thumbnails
        self.running = True
        self.websocket = None
        self.last_downloaded_image: Optional[Path] = None

        self.server_candidates = [server_url.strip()]
        if fallback_url and fallback_url.strip() != server_url.strip():
            self.server_candidates.append(fallback_url.strip())
        self.server_index = 0
        self._apply_server(self.server_candidates[0])

    def _apply_server(self, server_url: str):
        self.raw_server_url = server_url
        self.ws_url, self.http_base_url = normalize_urls(server_url)

    def print_welcome(self):
        """Prints a simple standard-line connection notice."""
        print(f"\n--- termchat connected ---")
        print(f"User:     {self.username}")
        print(f"Server:   {self.http_base_url}")
        print(f"Web UI:   {self.http_base_url} (open in browser to chat or send images)")
        if len(self.server_candidates) > 1:
            print(f"Fallback: {self.server_candidates[1]}")
        print(f"Commands: /help, /open (view last image), /quit")
        print(f"---------------------------\n")

    def handle_incoming_chat(self, msg: dict):
        sender = msg.get("sender", "Unknown")
        client_type = msg.get("client_type", "web")
        text = msg.get("text", "")

        badge = "[🌐 Web]" if client_type == "web" else "[💻 Terminal]"
        print(f"\n{badge} {sender}: {text}")

    def handle_incoming_image(self, msg: dict):
        sender = msg.get("sender", "Unknown")
        rel_url = msg.get("image_url", "")
        filename = msg.get("filename", "image.png")

        # Construct full URL
        full_url = f"{self.http_base_url}{rel_url}"

        print(f"\n[🌐 Web] {sender} 📷 Sent an image: {filename}")
        print(f"  URL: {full_url}")

        # Download locally
        saved_path = download_image(full_url, filename)
        if saved_path:
            self.last_downloaded_image = saved_path
            print(f"  Saved locally: {saved_path}")

            # Terminal ANSI thumbnail
            if self.show_thumbnails:
                thumb = render_ansi_thumbnail(saved_path, width=38)
                if thumb:
                    print("\n" + thumb + "\n")

            # Auto open if requested
            if self.auto_open_images:
                open_system_image(saved_path)

    def handle_incoming_system(self, msg: dict):
        text = msg.get("text", "")
        print(f"\n[System] {text}")

    def handle_incoming_ai(self, msg: dict):
        sender = msg.get("sender", "🤖 TermChat AI")
        text = msg.get("text", "")
        print(f"\n\033[1;35m{sender}\033[0m:")
        print("\033[36m──────────────────────────────────────────────────\033[0m")
        print(text)
        print("\033[36m──────────────────────────────────────────────────\033[0m\n")


    async def _receive_loop(self, ws):
        """Listens for messages from the online server."""
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                m_type = data.get("type")

                if m_type == "chat":
                    self.handle_incoming_chat(data)
                elif m_type == "image":
                    self.handle_incoming_image(data)
                elif m_type == "ai":
                    self.handle_incoming_ai(data)
                elif m_type == "system":
                    self.handle_incoming_system(data)
                elif m_type == "history":
                    history = data.get("messages", [])
                    if history:
                        print(f"--- Loaded {len(history)} recent message(s) ---")
                        for h in history:
                            if h.get("type") == "chat":
                                self.handle_incoming_chat(h)
                            elif h.get("type") == "image":
                                self.handle_incoming_image(h)
                            elif h.get("type") == "ai":
                                self.handle_incoming_ai(h)
                        print("------------------------------------------\n")

                elif m_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))

        except websockets.exceptions.ConnectionClosed:
            if self.running:
                print("\n[Server connection closed. Reconnecting...]")
        except Exception as e:
            if self.running:
                print(f"\n[Error receiving: {e}]")

    async def _input_loop(self, session: PromptSession):
        """Reads user input and sends it to the server."""
        while self.running:
            try:
                user_text = await session.prompt_async("> ")
                text = user_text.strip()
                if not text:
                    continue

                if text.startswith("/"):
                    cmd = text.lower().split()[0]
                    if cmd in ("/quit", "/exit", "/q"):
                        self.running = False
                        break
                    elif cmd == "/help":
                        print("\nAvailable commands:")
                        print("  /ai <question>  - Ask the free AI assistant any question directly")
                        print("  /open           - Open the last received image in your OS viewer")
                        print("  /web            - Print Web UI URL")
                        print("  /help           - Show help")
                        print("  /quit or /exit  - Exit chat\n")
                        continue
                    elif cmd == "/ai" and text == "/ai":
                        print("\nUsage: /ai <your question here>")
                        print("Example: /ai write a python script to download a webpage\n")
                        continue

                    elif cmd == "/web":
                        print(f"Web UI: {self.http_base_url}")
                        continue
                    elif cmd == "/open":
                        if self.last_downloaded_image and self.last_downloaded_image.exists():
                            print(f"Opening {self.last_downloaded_image}...")
                            open_system_image(self.last_downloaded_image)
                        else:
                            print("No images received yet.")
                        continue
                    else:
                        print(f"Unknown command '{cmd}'. Type /help for options.")
                        continue

                # Send message
                if self.websocket:
                    payload = {
                        "type": "chat",
                        "text": text,
                        "timestamp": datetime.now().isoformat(),
                    }
                    await self.websocket.send(json.dumps(payload))
                else:
                    print("[Not connected to server]")

            except (KeyboardInterrupt, EOFError):
                self.running = False
                break
            except Exception as e:
                print(f"[Input error: {e}]")

    async def run(self):
        """Main client loop with automatic reconnect and fallback server failover."""
        self.print_welcome()
        session = PromptSession()

        device = f"{platform.system()} ({platform.machine()})"
        query_params = urllib.parse.urlencode({
            "username": self.username,
            "client_type": "terminal",
            "device_info": device,
        })

        with patch_stdout():
            while self.running:
                full_ws = f"{self.ws_url}?{query_params}"
                try:
                    print(f"Connecting to {self.http_base_url}...")
                    async with websockets.connect(
                        full_ws,
                        ping_interval=25,
                        ping_timeout=15,
                        open_timeout=8,
                    ) as ws:
                        self.websocket = ws
                        print(f"Connected to {self.http_base_url}! Start typing text below (Press Enter to send):\n")

                        recv_task = asyncio.create_task(self._receive_loop(ws))
                        input_task = asyncio.create_task(self._input_loop(session))

                        done, pending = await asyncio.wait(
                            [recv_task, input_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        for t in pending:
                            t.cancel()
                            try:
                                await t
                            except asyncio.CancelledError:
                                pass

                        if not self.running:
                            break

                except (ConnectionRefusedError, OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as e:
                    if not self.running:
                        break
                    if len(self.server_candidates) > 1:
                        next_idx = (self.server_index + 1) % len(self.server_candidates)
                        next_server = self.server_candidates[next_idx]
                        print(f"\n[Warning] {self.http_base_url} unreachable ({e}).")
                        print(f"[Failover] Switching to fallback server: {next_server}...")
                        self.server_index = next_idx
                        self._apply_server(next_server)
                        await asyncio.sleep(1)
                    else:
                        print(f"Could not connect to {self.http_base_url}. Retrying in 3s... (Ctrl+C to exit)")
                        await asyncio.sleep(3)
                except Exception as e:
                    if not self.running:
                        break
                    if len(self.server_candidates) > 1:
                        next_idx = (self.server_index + 1) % len(self.server_candidates)
                        next_server = self.server_candidates[next_idx]
                        print(f"\n[Warning] Connection issue on {self.http_base_url}: {e}")
                        print(f"[Failover] Switching to fallback server: {next_server}...")
                        self.server_index = next_idx
                        self._apply_server(next_server)
                        await asyncio.sleep(1)
                    else:
                        print(f"Connection error: {e}. Retrying in 3s...")
                        await asyncio.sleep(3)

        print("\nExiting termchat. Goodbye!")


def start(
    server_url: str,
    username: str,
    fallback_url: Optional[str] = None,
    auto_open: bool = False,
    no_thumb: bool = False,
):
    client = TerminalClient(
        server_url=server_url,
        username=username,
        fallback_url=fallback_url,
        auto_open_images=auto_open,
        show_thumbnails=not no_thumb,
    )
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nExited.")
