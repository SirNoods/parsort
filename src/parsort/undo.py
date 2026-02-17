from __future__ import annotations

import json
import shutil
from pathlib import Path


def latest_run_log(inbox: Path) -> Path | None:
    logdir = inbox / ".parsort"
    if not logdir.exists():
        return None
    logs = sorted(logdir.glob("run_*.jsonl"))
    return logs[-1] if logs else None


def undo_last_run(inbox: Path, dry_run: bool = False) -> int:
    log = latest_run_log(inbox)
    if not log:
        raise SystemExit("No previous parsort runs found to undo.")

    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]

    # undo in reverse order
    count = 0
    for rec in reversed(records):
        src = Path(rec["src"])
        dst = Path(rec["dst"])

        # move file back from dst -> src
        if not dst.exists():
            continue
        src.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            count += 1
            continue

        shutil.move(str(dst), str(src))
        count += 1

    return count
