"""API keys: from the environment, or from a 0600 file we never log."""

from __future__ import annotations

import logging
import os
import stat
import tomllib

from . import paths

log = logging.getLogger(__name__)


def load_file() -> dict[str, str]:
    path = paths.secrets_file()
    if not path.exists():
        return {}
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        log.warning("%s is world- or group-readable; chmod 600 it", path)
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def resolve(key_env: str = "", key_name: str = "") -> str:
    """Look up a key: explicit env var first, then secrets.toml.

    Keys are never written into config.toml, so a config you paste into a
    chat or a gist does not leak credentials.
    """
    if key_env:
        value = os.environ.get(key_env, "")
        if value:
            return value
    stored = load_file()
    if key_name and key_name in stored:
        return stored[key_name]
    if key_env and key_env in stored:
        return stored[key_env]
    return ""


def redact(value: str) -> str:
    if not value:
        return "(unset)"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"
