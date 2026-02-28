"""
parsort.preview

Optional image preview helpers using `chafa`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import shutil

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff"}

def is_image(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in IMAGE_EXTS

def chafa_available() -> bool:
    return shutil.which("chafa") is not None

def show_image_with_chafa(path: Path, size: str = "60x30") -> None:
    """
    Render an image preview using chafa.

    `size` format: "WxH" (e.g. "60x30")
    """
    subprocess.run(["chafa", f"--size={size}", str(path)], check=False)