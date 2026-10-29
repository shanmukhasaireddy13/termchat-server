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
