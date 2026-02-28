from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "exr"}

def is_image(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in IMAGE_EXTS

def chafa_available() -> bool:
    return shutil.which("chafa") is not None

def clear_screen() -> None:
    os.system("clear")

@dataclass(frozen=True)
class ChafaOpts:
    size: str = "60*30"         # Width x Height
    symbols: str = "block"      # or "ascii", "unicode"
    dither: str | None = None   # e.g. "bayer", "none"

def render_with_chafa(path: Path, opts: ChafaOpts) -> None:
    cmd = ["chafa", f"--size={opts.size}", f"--symbols={opts.symbols}"]
    if opts.dither:
        cmd.append(f"--dither={opts.dither}")
    cmd.append(str(path))
    subprocess.run(cmd, check=False)