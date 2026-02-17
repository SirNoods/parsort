from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from .config import load_config
from .log import run_log_path, set_latest_run, write_record, MoveRecord
from .sorter import SkipRecord, sort_inbox, pick_rule, unique_destination
from .undo import undo_last_run
from .xdg import user_config_path
import shutil

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

def suggested_destination(cfg, file: Path) -> tuple[str, str] | None:
    rule = pick_rule(cfg, file)
    if not rule:
        return None
    return (rule.bucket, rule.path)

def bucket_menu_order(cfg) -> list[str]:
    # Prefer standard PARA order if present; otherwise fall back to config order
    preferred = ["projects", "areas", "resources", "archive"]
    keys = list(cfg.buckets.keys())
    ordered = [k for k in preferred if k in cfg.buckets]
    ordered += [k for k in keys if k not in ordered]
    return ordered

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

    missing = []
    for key, folder_name in buckets.items():
        bucket_path = para_root / folder_name
        if not bucket_path.exists():
            missing.append(bucket_path)

    if missing:
        print("\nThe following bucket directories do not exist:")
        for path in missing:
            print(f"  - {path}")

        create = input("\nCreate them now? [y/N]: ").strip().lower()
        if create == "y":
            for path in missing:
                path.mkdir(parents=True, exist_ok=True)
                print(f"Created: {path}")
        else:
            print("Skipping bucket creation. Make sure they exist before sorting.")

    cfg_path.write_text(config_template(para_root, buckets), encoding="utf-8")
    print(f"\nWrote config: {cfg_path}")
    return 0

def cmd_sort(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    cfg_path = resolve_config_path(args.config)

    cfg = load_config(cfg_path)

    # -------------------------
    # Guided mode: prompt for EVERY file
    # -------------------------
    if getattr(args, "guided", False):
        files = sorted([p for p in inbox.iterdir() if p.is_file()])
        confirmed: list[MoveRecord] = []
        skipped: list[SkipRecord] = []

        # Prefer PARA order if present
        preferred = ["projects", "areas", "resources", "archive"]
        bucket_keys = [k for k in preferred if k in cfg.buckets] + [
            k for k in cfg.buckets.keys() if k not in preferred
        ]

        for f in files:
            rule = pick_rule(cfg, f)  # suggestion only
            suggested_bucket = rule.bucket if rule else None
            suggested_path = rule.path if rule else ""
            suggested_label = (
                f"{suggested_bucket}/{suggested_path}".rstrip("/")
                if suggested_bucket
                else "(no suggestion)"
            )

            print("\n" + "-" * 50)
            print(f"File: {f.name}")
            print(f"From: {f}")
            print(f"Suggested: {suggested_label}")

            for i, k in enumerate(bucket_keys, start=1):
                print(f"  {i}) {k} ({cfg.buckets[k]})")
            print("  s) skip")
            print("  q) quit")

            # Choose bucket
            chosen_bucket: str | None = None
            subpath_default = ""

            while True:
                choice = input("> ").strip().lower()

                if choice == "q":
                    print("Quit.")
                    # stop prompting further files
                    f = None  # marker for quit
                    break

                if choice == "s":
                    skipped.append(SkipRecord(path=str(f), reason="user skipped"))
                    break

                if choice == "":
                    if not suggested_bucket:
                        print("No suggestion available. Choose a bucket number, s, or q.")
                        continue
                    chosen_bucket = suggested_bucket
                    subpath_default = suggested_path
                    break

                if choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(bucket_keys):
                        chosen_bucket = bucket_keys[idx - 1]
                        subpath_default = suggested_path if chosen_bucket == suggested_bucket else ""
                        break

                print("Invalid input. Use Enter, 1-9, s, or q.")

            # quit marker
            if f is None:
                break

            # skip marker
            if chosen_bucket is None:
                continue

            # Choose subfolder path (can be empty)
            subpath = input(f"Subfolder path [{subpath_default}]: ").strip() or subpath_default

            bucket_dir = cfg.buckets[chosen_bucket]
            if subpath:
                dest_dir = (cfg.para_root / bucket_dir / subpath).resolve()
            else:
                dest_dir = (cfg.para_root / bucket_dir).resolve()
            dest_dir.mkdir(parents=True, exist_ok=True)

            dst = unique_destination(dest_dir / f.name)

            # For now, log the original rule name if it existed; otherwise "guided"
            rule_name = rule.name if rule else "guided"

            confirmed.append(MoveRecord(src=str(f), dst=str(dst), rule=rule_name))

        # Guided dry-run output
        if args.dry_run:
            for m in confirmed:
                print(f"[DRY] {m.rule}: {m.src} -> {m.dst}")
            print(f"[DRY] would move {len(confirmed)} file(s)")
            print_unmatched(skipped)
            return 0

        if not confirmed:
            print("moved 0 file(s)")
            print_unmatched(skipped)
            return 0

        log_path = run_log_path(inbox)
        with log_path.open("w", encoding="utf-8") as fp:
            for m in confirmed:
                shutil.move(m.src, m.dst)
                write_record(fp, m)
                print(f"{m.rule}: {m.src} -> {m.dst}")

        set_latest_run(inbox, log_path)

        print(f"moved {len(confirmed)} file(s)")
        print_unmatched(skipped)
        print(f"log: {log_path}")
        return 0

    # -------------------------
    # Automatic mode
    # -------------------------
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

    log_path = run_log_path(inbox)
    with log_path.open("w", encoding="utf-8") as fp:
        for m in moves:
            write_record(fp, m)
            print(f"{m.rule}: {m.src} -> {m.dst}")

    set_latest_run(inbox, log_path)

    print(f"moved {len(moves)} file(s)")
    print_unmatched(skipped)
    print(f"log: {log_path}")
    return 0

def guided_plan_for_file(cfg, inbox: Path, file: Path) -> tuple[str, str] | None:
    sug = suggested_destination(cfg, file)
    suggested_text = "(no suggestion)"
    default_bucket = None
    default_subpath = ""

    if sug:
        default_bucket, default_subpath = sug
        suggested_text = f"{default_bucket}/{default_subpath}".rstrip("/")

    print("\n" + "-" * 50)
    print(f"File: {file.name}")
    print(f"From: {file}")
    print(f"Suggested: {suggested_text}")

    order = bucket_menu_order(cfg)
    for i, k in enumerate(order, start=1):
        print(f"  {i}) {k} ({cfg.buckets[k]})")
    print("  s) skip")
    print("  q) quit")

    while True:
        choice = input("> ").strip().lower()

        if choice in ("q",):
            return ("__QUIT__", "")

        if choice in ("s",):
            return None

        # Enter = accept suggestion (only if exists)
        if choice == "":
            if default_bucket is None:
                print("No suggestion available. Choose a bucket number, s, or q.")
                continue
            chosen_bucket = default_bucket
            subpath_default = default_subpath
            break

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(order):
                chosen_bucket = order[idx - 1]
                subpath_default = default_subpath if chosen_bucket == default_bucket else ""
                break

        print("Invalid input. Use Enter, 1-9, s, or q.")

    subpath = input(f"Subfolder path [{subpath_default}]: ").strip() or subpath_default

    bucket_dir = cfg.buckets[chosen_bucket]
    dest_dir = (cfg.para_root / bucket_dir / subpath).resolve() if subpath else (cfg.para_root / bucket_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    dst = unique_destination(dest_dir / file.name)
    # For logging, use the suggested rule name if it existed, otherwise "guided"
    rule_name = "guided"
    if sug and chosen_bucket == default_bucket and subpath == default_subpath:
        rule_name = "suggested"

    return (str(dst), rule_name)


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
    ps.add_argument("--guided", action="store_true", help="Prompt for every file; rules are suggestions only")
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
