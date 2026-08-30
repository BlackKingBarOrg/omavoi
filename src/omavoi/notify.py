"""Desktop notifications. Best-effort — a missing daemon must never break dictation."""

from __future__ import annotations

import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

# Replaces the previous Omavoi notification instead of stacking them up.
_SYNC_HINT = "string:x-canonical-private-synchronous:omavoi"


def send(summary: str, body: str = "", *, urgency: str = "normal", icon: str = "") -> None:
    if shutil.which("notify-send") is None:
        return
    argv = ["notify-send", "-a", "Omavoi", "-u", urgency, "-h", _SYNC_HINT]
    if icon:
        argv += ["-i", icon]
    argv += [summary]
    if body:
        argv.append(body)
    try:
        subprocess.run(argv, timeout=2, check=False, capture_output=True)
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug("notify-send failed: %s", exc)
