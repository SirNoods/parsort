from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .log import log_path_for_inbox, write_record
from .sorter import sort_inbox
from .undo import undo_last_run
from collections import Counter
from .sorter import sort_inbox, SkipRecord


def cmd_sort(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    cfg_path = Path(args.config).expanduser().resolve()

    cfg = load_config(cfg_path)
    moves, skipped = sort_inbox(inbox=inbox, cfg=cfg, dry_run=args.dry_run)

    if args.dry_run:
        for m in moves:
            print(f"[DRY] {m.rule}: {m.src} -> {m.dst}")
        print(f"[DRY] would move {len(moves)} file(s)")
        return 0

    log_path = log_path_for_inbox(inbox)
    with log_path.open("w", encoding="utf-8") as fp:
        for m in moves:
            write_record(fp, m)
            print(f"{m.rule}: {m.src} -> {m.dst}")
    if not moves:
        print("moved 0 file(s)")
        print_unmatched(skipped)
        return 0
    print(f"moved {len(moves)} file(s)")
    print_unmatched(skipped)
    print(f"log: {log_path}")
    return 0


def cmd_undo(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    n = undo_last_run(inbox=inbox, dry_run=args.dry_run)
    if args.dry_run:
        print(f"[DRY] would undo {n} move(s)")
    else:
        print(f"undid {n} move(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="parsort")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sort", help="Sort an inbox folder using rules")
    ps.add_argument("inbox", help="Folder to treat as inbox (e.g. ~/Downloads)")
    ps.add_argument("--config", default="default_config.yml", help="Path to config YAML")
    ps.add_argument("--dry-run", action="store_true", help="Show what would happen")
    ps.set_defaults(func=cmd_sort)

    pu = sub.add_parser("undo", help="Undo the last sort run")
    pu.add_argument("inbox", help="Inbox folder used previously")
    pu.add_argument("--dry-run", action="store_true", help="Show what would happen")
    pu.set_defaults(func=cmd_undo)

    return p

def print_unmatched(skipped: list[SkipRecord], limit: int = 20) -> None:
    if not skipped:
        return

    counts = Counter(s.reason for s in skipped)
    total = len(skipped)

    print("\nUnmatched / skipped:")
    for reason, n in counts.most_common():
        print(f"  - {reason}: {n}")

    print("\nExamples:")
    for rec in skipped[:limit]:
        print(f"  - {rec.reason}: {rec.path}")

    if total > limit:
        print(f"  ... and {total - limit} more")

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
