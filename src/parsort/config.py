from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
import sys


@dataclass(frozen=True)
class Rule:
    name: str
    match_ext: set[str]
    bucket: str
    path: str


@dataclass(frozen=True)
class Config:
    para_root: Path
    buckets: dict[str, str]   # key -> folder name
    rules: list[Rule]


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    para_root = Path(data.get("para_root", "~")).expanduser().resolve()
    buckets = {str(k): str(v) for k, v in (data.get("buckets") or {}).items()}

    rules: list[Rule] = []
    for r in data.get("rules", []):
        name = str(r.get("name", "unnamed"))
        exts = {e.lower().lstrip(".") for e in (r.get("ext") or [])}
        bucket = str(r.get("bucket", "")).strip()
        relpath = str(r.get("path", "")).strip()

        if not bucket:
            print(f"Config warning: rule '{name}' has no bucket", file=sys.stderr)
            continue
        if bucket not in buckets:
            print(
                f"Config warning: rule '{name}' references unknown bucket '{bucket}'. "
                f"Known: {sorted(buckets.keys())}",
                file=sys.stderr,
            )
            continue

        rules.append(Rule(name=name, match_ext=exts, bucket=bucket, path=relpath))

    return Config(para_root=para_root, buckets=buckets, rules=rules)
