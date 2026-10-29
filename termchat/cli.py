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
    PRIMARY_DEFAULT_SERVER,
    get_default_servers,
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

    # Handle direct one-shot CLI commands: `termchat run ...`, `termchat setup-lyra`, `termchat export-codes`, etc.
    if args.ai_prompt:
        prompt_words = list(args.ai_prompt)
        first_word = prompt_words[0].lower() if prompt_words else ""

        if first_word == "run":
            from termchat.codes.runner import run_script, list_available
            if len(prompt_words) < 2 or prompt_words[1].lower() in ("list", "-h", "--help"):
                list_available()
                sys.exit(0)
            sys.exit(run_script(prompt_words[1], prompt_words[2:]))

        elif first_word in ("setup-lyra", "setup_lyra", "install-lyra"):
            from termchat.codes.runner import setup_lyra_workspace
            sys.exit(setup_lyra_workspace())

        elif first_word in ("export-codes", "export"):
            from termchat.codes.runner import export_codes
            dest = prompt_words[1] if len(prompt_words) > 1 else None
            sys.exit(export_codes(dest))

        elif first_word in ("codes", "list-codes"):
            from termchat.codes.runner import run_script, list_available, setup_lyra_workspace, export_codes
            sub_args = prompt_words[1:]
            if not sub_args or sub_args[0].lower() in ("list", "-h", "--help"):
                list_available()
                sys.exit(0)
            sub_cmd = sub_args[0].lower()
            if sub_cmd == "run" and len(sub_args) > 1:
                sys.exit(run_script(sub_args[1], sub_args[2:]))
            elif sub_cmd in ("setup-lyra", "setup_lyra"):
                sys.exit(setup_lyra_workspace())
            elif sub_cmd in ("export", "export-codes"):
                dest = sub_args[1] if len(sub_args) > 1 else None
                sys.exit(export_codes(dest))
            else:
                sys.exit(run_script(sub_cmd, sub_args[1:]))

        # Handle direct one-shot CLI AI query: `termchat ai "my question"`
        if prompt_words and prompt_words[0].lower() in ("ai", "ask"):
            prompt_words = prompt_words[1:]
        question = " ".join(prompt_words).strip()
        if question:
            saved_key = get_saved_ai_key()
            print(f"\n[TermChat AI] Thinking...")
            answer = query_llm(question, custom_key=saved_key)
            print(f"\n{answer}\n")
            sys.exit(0)


    # Determine server URL and fallback failover
    primary_srv, fallback_srv = get_default_servers()
    if args.server:
        server_url = args.server.strip()
        fallback_url = None
    else:
        server_url = primary_srv
        fallback_url = fallback_srv

    # Determine username
    username = args.name or get_saved_username()

    start(
        server_url=server_url,
        username=username,
        fallback_url=fallback_url,
        auto_open=args.open,
        no_thumb=args.no_thumb,
    )


if __name__ == "__main__":
    main()
