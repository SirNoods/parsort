from __future__ import annotations

import json
import shutil
from pathlib import Path

from .log import get_latest_run


def undo_last_run(inbox: Path, dry_run: bool = False) -> int:
    log = get_latest_run(inbox)
    if not log:
        raise SystemExit("No previous parsort runs found to undo for this inbox.")

    records = [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    count = 0
    for rec in reversed(records):
        src = Path(rec["src"])
        dst = Path(rec["dst"])

        if not dst.exists():
            continue

        src.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            count += 1
            continue

        shutil.move(str(dst), str(src))
        count += 1

    return count
