import io
from pathlib import Path
from PIL import Image
import pytest
from termchat.viewer import render_ansi_thumbnail


def test_render_ansi_thumbnail(tmp_path):
    # Create a small 4x4 test image
    img = Image.new("RGB", (4, 4), color="blue")
    test_file = tmp_path / "test.png"
    img.save(test_file)

    thumb = render_ansi_thumbnail(test_file, width=4)
    assert thumb is not None
    assert "\033[" in thumb  # Contains ANSI escape codes
