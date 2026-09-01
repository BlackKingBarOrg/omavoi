"""The Claude Code CLI as an LLM step.

Worth having because it needs no API key: it reuses whatever `claude` is
already logged in as, so a machine that already has Claude Code set up gets an
LLM pass for free.

The cost is startup. Claude Code boots a whole session per invocation, which
measured around 8.5 s here against roughly a second for a direct API call, and
neither --strict-mcp-config nor --no-session-persistence moves it. So this
belongs in a mode you reach for deliberately — a translation pass — rather
than on every take.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import Any

from .base import LlmResult

log = logging.getLogger(__name__)


class ClaudeCliBackend:
    def __init__(self, name: str, cfg: dict[str, Any]) -> None:
        self.name = name
        self.backend = "claude-cli"
        self.binary = str(cfg.get("binary", "") or "claude")
        self.model = str(cfg.get("model", "") or "haiku")
        self.timeout = float(cfg.get("timeout", 60.0))

    def state(self) -> dict[str, Any]:
        found = shutil.which(self.binary)
        return {
            "name": self.name,
            "backend": self.backend,
            "engine": "claude-cli",
            "model": self.model,
            # The process is local; the inference is not.
            "remote": True,
            # Nothing stays resident — each take spawns the CLI — so being on
            # PATH is as ready as this backend gets.
            "live": bool(found),
            "url": found or "",
            "pid": 0,
            "problem": "" if found else f"{self.binary} is not on PATH",
        }

    def describe(self) -> str:
        st = self.state()
        return (f"{self.name}: claude-cli {st['model']} "
                f"({st['url'] or 'claude not on PATH'})")

    def complete(self, system: str, text: str, *, timeout: float = 0.0) -> LlmResult:
        started = time.monotonic()
        found = shutil.which(self.binary)
        if not found:
            return LlmResult("", self.model, self.backend, 0.0,
                             error=f"{self.binary} is not on PATH")

        argv = [found, "-p", "--model", self.model, "--allowed-tools", ""]
        if system.strip():
            argv += ["--system-prompt", system]

        try:
            # The transcript goes in on stdin, not argv: a long dictation would
            # otherwise run into ARG_MAX, and it keeps quoting out of the way.
            proc = subprocess.run(
                argv, input=text.encode(), capture_output=True,
                timeout=timeout or self.timeout,
            )
        except subprocess.TimeoutExpired:
            return LlmResult("", self.model, self.backend, time.monotonic() - started,
                             error=f"timed out after {timeout or self.timeout:.0f}s")
        except OSError as exc:
            return LlmResult("", self.model, self.backend, time.monotonic() - started,
                             error=str(exc))

        if proc.returncode != 0:
            return LlmResult("", self.model, self.backend, time.monotonic() - started,
                             error=proc.stderr.decode("utf-8", "replace")[:200].strip()
                                   or f"claude exited {proc.returncode}")

        return LlmResult(proc.stdout.decode("utf-8", "replace").strip(),
                         self.model, self.backend, time.monotonic() - started)
