"""
CLI interface for termchat client.
"""

import argparse
import os
import sys

from termchat import __version__
from termchat.ai import query_llm
from termchat.client import start
from termchat.config import (
    DEFAULT_FALLBACK_SERVER,
    get_saved_ai_key,
    get_saved_server_url,
    get_saved_username,
    set_saved_ai_key,
    set_saved_server_url,
    set_saved_username,
)



def main():
    parser = argparse.ArgumentParser(
        prog="termchat",
        description="Non-intrusive terminal chat client connecting to your online Render/cloud server.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"termchat {__version__}")
    parser.add_argument(
        "-s",
        "--server",
        help="Online server URL (e.g. https://my-chat.onrender.com). Overrides saved config.",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="Chat username. Overrides saved config.",
    )
    parser.add_argument(
        "--set-server",
        help="Save a default online server URL to ~/.termchat.json and exit.",
    )
    parser.add_argument(
        "--set-name",
        help="Save a default username to ~/.termchat.json and exit.",
    )
    parser.add_argument(
        "--set-ai-key",
        help="Save an AI API key (Kilo, Groq, OpenRouter) to ~/.termchat.json and exit.",
    )
    parser.add_argument(
        "ai_prompt",
        nargs="*",
        help="Directly ask a question to the AI assistant (e.g. termchat ai 'how does async work?')",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open received images in your OS default image viewer.",
    )

    parser.add_argument(
        "--no-thumb",
        action="store_true",
        help="Disable ANSI image thumbnail previews in the terminal.",
    )

    args = parser.parse_args()

    # Handle configuration saving
    if args.set_server:
        set_saved_server_url(args.set_server)
        print(f"[OK] Default server saved: {args.set_server}")
        sys.exit(0)

    if args.set_name:
        set_saved_username(args.set_name)
        print(f"[OK] Default username saved: {args.set_name}")
        sys.exit(0)

    if args.set_ai_key:
        set_saved_ai_key(args.set_ai_key)
        print(f"[OK] AI API key saved to ~/.termchat.json")
        sys.exit(0)

    # Handle direct one-shot CLI AI query: `termchat ai "my question"`
    if args.ai_prompt:
        prompt_words = list(args.ai_prompt)
        if prompt_words and prompt_words[0].lower() in ("ai", "ask"):
            prompt_words = prompt_words[1:]
        question = " ".join(prompt_words).strip()
        if question:
            saved_key = get_saved_ai_key()
            print(f"\n[TermChat AI] Thinking...")
            answer = query_llm(question, custom_key=saved_key)
            print(f"\n{answer}\n")
            sys.exit(0)


    # Determine server URL (defaults directly to live Singapore Render server)
    server_url = (args.server or get_saved_server_url() or DEFAULT_FALLBACK_SERVER).strip()

    # Determine username
    username = args.name or get_saved_username()

    start(
        server_url=server_url,
        username=username,
        auto_open=args.open,
        no_thumb=args.no_thumb,
    )


if __name__ == "__main__":
    main()
