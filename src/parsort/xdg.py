from __future__ import annotations

import os
from pathlib import Path


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

def user_config_path() -> Path:
    return xdg_config_home() / "parsort" / "config.yml"

def xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))

def state_dir() -> Path:
    return xdg_state_home() / "parsort"