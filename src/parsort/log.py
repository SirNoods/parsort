from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

@dataclass
class MoveRecord:
    src: str
    dst: str
    rule: str


def log_path_for_inbox(inbox: Path) -> Path:
    # keep logs alongside the inbox, hidden folder
    logdir = inbox / ".parsort"
    logdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return logdir / f"run_{stamp}.jsonl"


def write_record(fp, rec: MoveRecord) -> None:
    fp.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")