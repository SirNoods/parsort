from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Config, Rule
from .log import MoveRecord


@dataclass
class SkipRecord:
    path: str
    reason: str


def pick_rule(cfg: Config, file: Path) -> Rule | None:
    ext = file.suffix.lower().lstrip(".")
    if not ext:
        return None
    for rule in cfg.rules:
        if ext in rule.match_ext:
            return rule
    return None


def unique_destination(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suf = dst.stem, dst.suffix
    parent = dst.parent
    i = 2
    while True:
        candidate = parent / f"{stem} ({i}){suf}"
        if not candidate.exists():
            return candidate
        i += 1


def sort_inbox(inbox: Path, cfg: Config, dry_run: bool = False):
    moves: list[MoveRecord] = []
    skipped: list[SkipRecord] = []

    for p in inbox.iterdir():
        if p.is_dir():
            if p.name == ".parsort":
                continue
            skipped.append(SkipRecord(path=str(p), reason="directory"))
            continue

        if not p.suffix:
            skipped.append(SkipRecord(path=str(p), reason="no extension"))
            continue

        rule = pick_rule(cfg, p)
        if not rule:
            skipped.append(SkipRecord(path=str(p), reason=f"no rule for .{p.suffix.lstrip('.').lower()}"))
            continue

        bucket_dir = cfg.buckets[rule.bucket]
        if bucket_dir:
            dest_dir = (cfg.para_root / bucket_dir / rule.path).resolve()
        else:
            dest_dir = (cfg.para_root / rule.path).resolve()

        dest_dir.mkdir(parents=True, exist_ok=True)
        dst = unique_destination(dest_dir / p.name)

        moves.append(MoveRecord(src=str(p), dst=str(dst), rule=rule.name))

        if not dry_run:
            shutil.move(str(p), str(dst))

    return moves, skipped