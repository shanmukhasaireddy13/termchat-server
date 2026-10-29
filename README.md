# termchat-client 💬🖼️🤖

[![PyPI version](https://img.shields.io/pypi/v/termchat-client.svg)](https://pypi.org/project/termchat-client/)
[![Python versions](https://img.shields.io/pypi/pyversions/termchat-client.svg)](https://pypi.org/project/termchat-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![OS Support](https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20Raspberry%20Pi%20%7C%20macOS-success)](https://pypi.org/project/termchat-client/)

**termchat-client** is a lightweight, non-intrusive terminal chat client packaged for Python. It connects directly to an online chat server (running on **Render** or any cloud host), allowing you to chat seamlessly between your **terminal** and an **online HTML web page** viewed by others, plus a **built-in free fast AI assistant** (supporting Kilo Code, Groq, OpenRouter, and Ollama) that answers coding and general questions directly!

---

## 💡 How It Works

- **Standard Terminal Interaction**: It does **not** change or take over your terminal UI. No fullscreen ncurses/curses screens. Just a normal, standard prompt line where you type text and press Enter.
- **🤖 Built-in Free AI Chat (Like Kilo Code / Groq)**:
  - Type `/ai <question>` or `@ai <question>` in terminal or click **🤖** on the web page to get direct answers from fast LLMs (LLaMA 3.3 70B, Qwen Coder, DeepSeek R1, Kilo Auto Free).
  - Also run one-shot questions directly from your shell: `termchat ai "write a python script to parse json"`.
- **Bi-Directional Messaging**:
  - You type text in your terminal ➔ It appears instantly on the web page.
  - Web users type replies ➔ They print right into your terminal: `[🌐 WebUser]: Hello from Chrome!`
- **Image Support to Terminal**:
  - Web users can click the image picker, drag & drop images, or **press `Ctrl+V` to paste screenshots directly from their clipboard**!
  - When an image is sent from the web, your terminal automatically downloads it into `./downloads/`, prints the URL, and renders a compact **ANSI 24-bit color block thumbnail preview**!
  - Open in native image viewer with `/open` or `--open`.
- **Works on Any OS**: Windows, Linux, **Raspberry Pi** (ARMv7 / aarch64), and macOS.


---

## 🏛️ System Architecture

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                 Online Server on Render                     │
 │          (FastAPI + WebSockets + Image Upload API)          │
 │              https://my-chat.onrender.com                   │
 └──────────────▲───────────────────────────────▲──────────────┘
                │                               │
     WebSocket  │                    WebSocket  │  + HTTP Web UI
     Connection │                    Connection │  (HTML5 / CSS / JS)
                │                               │
  ┌─────────────┴──────────┐      ┌─────────────┴─────────────┐
  │  termchat-client (CLI) │      │      Web Client (HTML)    │
  │  • Linux / Raspberry Pi│      │  • Desktop Browsers       │
  │  • Windows CMD / PS    │      │  • Mobile Browsers (iOS)  │
  │  • macOS Terminal      │      │  • Paste Images (Ctrl+V)  │
  │  (Just text in & out)  │      │  • Drag & Drop Images     │
  └────────────────────────┘      └───────────────────────────┘
```

---

## 📦 Installation

Install the client package on any machine:

```bash
pip install termchat-client
```

---

## 🚀 Terminal Client Usage

### 1. Run via CLI
```bash
termchat --server https://my-chat.onrender.com --name Alice
```
Or via Python module:
```bash
python -m termchat --server https://my-chat.onrender.com --name Alice
```

### 2. Save Your Server Once
Save your online server URL so you never need to type it again:
```bash
termchat --set-server https://my-chat.onrender.com
termchat --set-name Alice
```
Once saved, simply run:
```bash
termchat
```
or:
```bash
python -m termchat
```

### 3. What It Looks Like in Your Terminal:
```text
--- termchat connected ---
User:   Alice
Server: https://my-chat.onrender.com
Web UI: https://my-chat.onrender.com
Commands: /help, /open (view last image), /quit
---------------------------

Connected! Start typing text below (Press Enter to send):

> Hello from my Raspberry Pi terminal!

[🌐 Web] Bob: Hey Alice! Check out this screenshot:
[🌐 Web] Bob 📷 Sent an image: dashboard.png
  URL: https://my-chat.onrender.com/uploads/dashboard.png
  Saved locally: C:\projects\terminal-chat\downloads\dashboard.png

  [ANSI Image Thumbnail rendered here]

> 
```

### In-Terminal Commands:
- `/open` — Opens the last received image in your OS default image viewer (Photos, Preview, or `xdg-open`).
- `/web` — Prints the Web UI link.
- `/help` — Lists available commands.
- `/quit` (or `Ctrl+C`) — Safely exits.

### Optional Flags:
- `--open`: Automatically opens any received image in your OS default image viewer.
- `--no-thumb`: Disables terminal ANSI thumbnail previews (prints URL and saved path only).

---

## 🌐 Deploying the Server to Render (Free)

The server code lives in the `server/` directory and can be deployed to [Render](https://render.com) in 2 minutes for free.

See [DEPLOY_RENDER.md](DEPLOY_RENDER.md) for full instructions:
1. Push this repository to GitHub.
2. In Render, click **New + > Web Service** and connect your GitHub repo.
3. Set **Root Directory** to `server`.
4. Set **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Deploy! Render gives you a live HTTPS and WebSocket URL like `https://my-chat.onrender.com`.

---

## 📤 Publishing to PyPI

The package is packaged using modern PEP 517 / PEP 621 (`pyproject.toml`).

1. Build distributions:
   ```bash
   python -m build
   ```
2. Verify with Twine:
   ```bash
   twine check dist/*
   ```
3. Upload to PyPI:
   ```bash
   twine upload dist/*
   ```
   *(Or run the included interactive helper: `python publish.py`)*

See [PUBLISHING.md](PUBLISHING.md) for step-by-step instructions.

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m pytest -v
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
