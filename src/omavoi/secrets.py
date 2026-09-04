"""API keys: from the environment, or from a 0600 file we never log."""

from __future__ import annotations

import logging
import os
import stat
import tomllib

from . import paths

log = logging.getLogger(__name__)


def store(name: str, value: str) -> None:
    """Write one key into the 0600 file, leaving the others alone.

    Never through a command line: a value in argv is readable from /proc by
    every process running as this user for as long as the command lives. The
    only caller reads it from stdin.
    """
    path = paths.secrets_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = load_file()
    if value:
        stored[str(name)] = str(value)
    else:
        stored.pop(str(name), None)
    body = "".join(
        f'{k} = "{v.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"\n'
        for k, v in sorted(stored.items())
    )
    # Created 0600 before anything is in it, rather than written and then
    # chmodded, which leaves a window where it is readable.
    tmp = path.with_suffix(".toml.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("# Written by `omavoi secrets set`. Never in config.toml.\n")
            fh.write(body)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def source_of(key_env: str = "", key_name: str = "") -> str:
    """Where a key would come from: "env", "file", or "" if there is none.

    Worth saying out loud, because the environment wins over the file — a
    stale env var silently beats the key you just pasted.
    """
    if key_env and os.environ.get(key_env):
        return "env"
    stored = load_file()
    if (key_name and key_name in stored) or (key_env and key_env in stored):
        return "file"
    return ""


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
