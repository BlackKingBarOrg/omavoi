"""XDG paths, in one place."""

from __future__ import annotations

import os
from pathlib import Path


def _xdg(var: str, default: str) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else Path.home() / default


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "omavoi"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "omavoi"


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "omavoi"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "omavoi"


def runtime_dir() -> Path:
    value = os.environ.get("XDG_RUNTIME_DIR")
    return Path(value) if value else Path(f"/run/user/{os.getuid()}")


def hf_cache_dir() -> Path:
    value = os.environ.get("HF_HUB_CACHE")
    if value:
        return Path(value)
    home = os.environ.get("HF_HOME")
    if home:
        return Path(home) / "hub"
    return _xdg("XDG_CACHE_HOME", ".cache") / "huggingface" / "hub"


def config_file() -> Path:
    return config_dir() / "config.toml"


def secrets_file() -> Path:
    return config_dir() / "secrets.toml"


def socket_file() -> Path:
    return runtime_dir() / "omavoi.sock"


def history_file() -> Path:
    return state_dir() / "history.jsonl"


def log_file() -> Path:
    return state_dir() / "omavoi.log"


def recordings_dir() -> Path:
    return cache_dir() / "recordings"
