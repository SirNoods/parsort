from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .xdg import state_dir


@dataclass
class MoveRecord:
    src: str
    dst: str
    rule: str


def inbox_key(inbox: Path) -> str:
    # Stable per-inbox key based on resolved absolute path
    p = str(inbox.expanduser().resolve())
    return hashlib.sha256(p.encode("utf-8")).hexdigest()[:16]


def run_log_path(inbox: Path) -> Path:
    base = state_dir() / "runs" / inbox_key(inbox)
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base / f"run_{stamp}.jsonl"


def latest_pointer_path(inbox: Path) -> Path:
    base = state_dir() / "runs" / inbox_key(inbox)
    base.mkdir(parents=True, exist_ok=True)
    return base / "latest.txt"


def set_latest_run(inbox: Path, log_path: Path) -> None:
    latest = latest_pointer_path(inbox)
    latest.write_text(str(log_path), encoding="utf-8")


def get_latest_run(inbox: Path) -> Path | None:
    latest = latest_pointer_path(inbox)
    if not latest.exists():
        return None
    p = Path(latest.read_text(encoding="utf-8").strip())
    return p if p.exists() else None


def write_record(fp, rec: MoveRecord) -> None:
    fp.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")