"""
Image viewer and thumbnail renderer for terminal clients.
Handles automatic downloading, terminal ANSI color block preview,
and launching the OS default image viewer.
"""

import io
import os
from pathlib import Path
import platform
import subprocess
import urllib.request
from typing import Optional


def get_downloads_dir() -> Path:
    """Returns local downloads directory."""
    d = Path.cwd() / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_image(full_image_url: str, filename: str) -> Optional[Path]:
    """Downloads image to local downloads folder."""
    try:
        dest_dir = get_downloads_dir()
        safe_name = Path(filename).name
        dest_path = dest_dir / safe_name

        req = urllib.request.Request(
            full_image_url,
            headers={"User-Agent": "termchat-terminal-client/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())

        return dest_path
    except Exception as e:
        return None


def open_system_image(filepath: Path):
    """Opens image in OS default viewer (Photos, Preview, or xdg-open)."""
    try:
        sys_name = platform.system()
        if sys_name == "Windows":
            os.startfile(str(filepath))
        elif sys_name == "Darwin":
            subprocess.run(["open", str(filepath)], check=False)
        else:
            subprocess.run(["xdg-open", str(filepath)], check=False)
    except Exception:
        pass


def render_ansi_thumbnail(filepath: Path, width: int = 36) -> Optional[str]:
    """
    Renders an image as an ANSI 24-bit color half-block thumbnail.
    Each terminal character '▀' has both foreground (top pixel) and background (bottom pixel).
    Works in Windows Terminal, Linux, macOS, and Raspberry Pi consoles with 24-bit color support.
    """
    try:
        from PIL import Image

        img = Image.open(filepath).convert("RGB")
        orig_w, orig_h = img.size
        # Half blocks have 1:2 aspect ratio in terminal fonts
        aspect = orig_h / orig_w
        height = int(width * aspect * 0.5)
        # Ensure even height for half-block pairing
        if height % 2 != 0:
            height += 1
        height = max(height, 2)

        resized = img.resize((width, height), Image.Resampling.BILINEAR)
        pixels = resized.load()

        lines = []
        for y in range(0, height, 2):
            line = []
            for x in range(width):
                r1, g1, b1 = pixels[x, y]
                if y + 1 < height:
                    r2, g2, b2 = pixels[x, y + 1]
                else:
                    r2, g2, b2 = (0, 0, 0)
                # ▀ is upper half block: fg is top pixel, bg is bottom pixel
                line.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀\033[0m")
            lines.append("".join(line))

        return "\n".join(lines)
    except Exception:
        return None
