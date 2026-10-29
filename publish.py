"""
Convenience publishing script for termchat-client.
Builds the package and uploads it to PyPI or TestPyPI using token in .env or manual entry.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def get_token_from_env() -> str:
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8").strip()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("pypi-"):
                return line
            if "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip("'\"")
                if v.startswith("pypi-"):
                    return v
    return ""


def run(cmd: str, env=None):
    print(f"\n[EXEC] {cmd}")
    ret = subprocess.call(cmd, shell=True, env=env)
    if ret != 0:
        print(f"\n[ERROR] Command failed with code {ret}")
        sys.exit(ret)


def main():
    print("=" * 60)
    print(" termchat-client: PyPI Build & Publish Utility")
    print("=" * 60)

    token = get_token_from_env()
    if token:
        print(f"[INFO] Detected PyPI API token from .env ({token[:12]}...)")

    print("\nSelect an action:")
    print("  1) Clean & Build distributions (.whl and .tar.gz)")
    print("  2) Validate distributions with twine check")
    print("  3) Upload to TestPyPI (sandbox test)")
    print("  4) Upload to Official PyPI (production release)")
    print("  5) Exit")

    choice = input("\nEnter choice [1-5]: ").strip()

    if choice == "1":
        print("\nCleaning old build artifacts...")
        for folder in ["dist", "build", "termchat_client.egg-info"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        run(f"{sys.executable} -m build")

    elif choice == "2":
        run(f"{sys.executable} -m twine check dist/*")

    elif choice == "3":
        run(f"{sys.executable} -m twine upload --repository testpypi dist/*")

    elif choice == "4":
        env = os.environ.copy()
        if token:
            env["TWINE_USERNAME"] = "__token__"
            env["TWINE_PASSWORD"] = token

        confirm = input("\nUpload to official PyPI? (yes/no): ").strip().lower()
        if confirm == "yes":
            run(f"{sys.executable} -m twine upload dist/*", env=env)
        else:
            print("Upload cancelled.")

    print("\nDone!")


if __name__ == "__main__":
    main()
