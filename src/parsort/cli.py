from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from .config import load_config
from .log import log_path_for_inbox, write_record
from .sorter import SkipRecord, sort_inbox
from .undo import undo_last_run
from .xdg import user_config_path

def config_template(para_root: Path, buckets: dict[str, str]) -> str:
    return f"""\
para_root: "{para_root}"

buckets:
  projects: {buckets["projects"]}
  areas: {buckets["areas"]}
  resources: {buckets["resources"]}
  archive: {buckets["archive"]}

rules:
  - name: Images
    ext: [png, jpg, jpeg, gif, webp]
    bucket: resources
    path: Images

  - name: Archives
    ext: [zip, rar, 7z, tar, gz]
    bucket: archive
    path: Archives

  - name: PDFs
    ext: [pdf]
    bucket: resources
    path: PDFs
"""

def default_config_template() -> str:
    home = Path.home()
    buckets = {
        "projects": "1_Projects",
        "areas": "2_Areas",
        "resources": "3_Resources",
        "archive": "4_Archive",
    }
    return config_template(home, buckets)

def prompt(question: str, default: str) -> str:
    ans = input(f"{question} [{default}]: ").strip()
    return ans or default

def resolve_config_path(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()

    ucp = user_config_path()
    if ucp.exists():
        return ucp

    # fallback: project-local default_config.yml
    return Path("default_config.yml").resolve()


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


def cmd_init(args: argparse.Namespace) -> int:
    cfg_path = user_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    if cfg_path.exists() and not args.force:
        print(f"Config already exists: {cfg_path}")
        print("Use --force to overwrite.")
        return 0

    if not args.guided:
        cfg_path.write_text(default_config_template(), encoding="utf-8")
        print(f"Wrote config: {cfg_path}")
        return 0

    # Guided mode
    print("Parsort init (guided). Press Enter to accept defaults.\n")

    para_root_str = prompt("PARA root folder", str(Path.home()))
    para_root = Path(para_root_str).expanduser().resolve()

    buckets = {
        "projects": prompt("Projects bucket folder", "1_Projects"),
        "areas": prompt("Areas bucket folder", "2_Areas"),
        "resources": prompt("Resources bucket folder", "3_Resources"),
        "archive": prompt("Archive bucket folder", "4_Archive"),
    }

    cfg_path.write_text(config_template(para_root, buckets), encoding="utf-8")
    print(f"\nWrote config: {cfg_path}")
    return 0

def cmd_sort(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    cfg_path = resolve_config_path(args.config)

    cfg = load_config(cfg_path)
    moves, skipped = sort_inbox(inbox=inbox, cfg=cfg, dry_run=args.dry_run)

    if args.dry_run:
        for m in moves:
            print(f"[DRY] {m.rule}: {m.src} -> {m.dst}")
        print(f"[DRY] would move {len(moves)} file(s)")
        print_unmatched(skipped)
        return 0

    if not moves:
        print("moved 0 file(s)")
        print_unmatched(skipped)
        return 0

    log_path = log_path_for_inbox(inbox)
    with log_path.open("w", encoding="utf-8") as fp:
        for m in moves:
            write_record(fp, m)
            print(f"{m.rule}: {m.src} -> {m.dst}")

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

    pi = sub.add_parser("init", help="Create a user config at ~/.config/parsort/config.yml")
    pi.add_argument("--guided", action="store_true", help="Run interactive setup")
    pi.add_argument("--force", action="store_true", help="Overwrite existing config")
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("sort", help="Sort an inbox folder using rules")
    ps.add_argument("inbox", help="Folder to treat as inbox (e.g. ~/Downloads)")
    ps.add_argument("--config", default=None, help="Path to config YAML (overrides user config)")
    ps.add_argument("--dry-run", action="store_true", help="Show what would happen")
    ps.set_defaults(func=cmd_sort)

    pu = sub.add_parser("undo", help="Undo the last sort run")
    pu.add_argument("inbox", help="Inbox folder used previously")
    pu.add_argument("--dry-run", action="store_true", help="Show what would happen")
    pu.set_defaults(func=cmd_undo)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
