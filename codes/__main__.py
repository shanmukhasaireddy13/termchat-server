"""
termchat.codes CLI entry point.
Allows:
  python3 -m termchat.codes run obstacle
  python3 -m termchat.codes list
  python3 -m termchat.codes setup-lyra
  python3 -m termchat.codes export [destination]
"""

import sys
from termchat.codes.runner import (
    run_script,
    list_available,
    setup_lyra_workspace,
    export_codes,
)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help", "list"):
        list_available()
        return 0

    cmd = args[0].lower().strip()
    if cmd == "run":
        if len(args) < 2:
            print("[Error] Specify a script name to run, e.g.: termchat run obstacle")
            list_available()
            return 1
        return run_script(args[1], args[2:])

    elif cmd in ("setup-lyra", "setup_lyra", "install-lyra"):
        return setup_lyra_workspace()

    elif cmd in ("export", "export-codes"):
        dest = args[1] if len(args) > 1 else None
        return export_codes(dest)

    else:
        # Treat as script name directly
        return run_script(cmd, args[1:])


if __name__ == "__main__":
    sys.exit(main())
