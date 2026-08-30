"""Getting text into the focused window.

Two paths, because neither one works everywhere:

  wtype      — virtual-keyboard protocol. Correct for native Wayland apps,
               but Electron and XWayland clients drop characters or ignore
               it outright.
  clipboard  — wl-copy plus a synthetic paste shortcut. Works essentially
               everywhere, at the cost of touching the user's clipboard,
               so we put the old contents back afterwards.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any

from .window import Window

log = logging.getLogger(__name__)


@dataclass(slots=True)
class InjectResult:
    ok: bool
    method: str
    seconds: float
    error: str = ""
    fell_back: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "method": self.method,
            "seconds": round(self.seconds, 3),
            "error": self.error, "fell_back": self.fell_back,
        }


class Injector:
    def __init__(self, cfg: dict[str, Any]) -> None:
        inject = cfg["inject"]
        self.method: str = inject.get("method", "auto")
        self.clipboard_classes = [c.lower() for c in inject.get("clipboard_classes", [])]
        self.restore_after = float(inject.get("restore_clipboard_after", 1.5))
        self.wtype_delay_ms = int(inject.get("wtype_delay_ms", 0))
        self.default_paste_key: str = inject.get("paste_key", "CTRL+V")
        self.avoid_wtype_on_xwayland = bool(inject.get("avoid_wtype_on_xwayland", True))
        self.paste_settle_ms = int(inject.get("paste_settle_ms", 60))

    # -- routing -----------------------------------------------------------

    def choose(self, win: Window, profile: dict[str, Any]) -> str:
        override = profile.get("inject")
        if override in ("wtype", "clipboard"):
            return str(override)
        if self.method in ("wtype", "clipboard"):
            return self.method

        # XWayland clients never see the keymap wtype installs for its virtual
        # keyboard, so they decode its keycodes against the system layout and
        # type digits instead of your words. Detecting the client is better
        # than listing them: it covers every X11 app without anyone keeping a
        # list up to date.
        if self.avoid_wtype_on_xwayland and win.xwayland:
            return "clipboard"

        haystack = f"{win.cls} {win.title}".lower()
        if any(c and c in haystack for c in self.clipboard_classes):
            return "clipboard"
        return "wtype"

    def inject(self, text: str, win: Window, profile: dict[str, Any] | None = None) -> InjectResult:
        profile = profile or {}
        if not text:
            return InjectResult(True, "noop", 0.0)

        method = self.choose(win, profile)
        started = time.monotonic()
        try:
            if method == "wtype":
                self._wtype(text)
            else:
                self._clipboard(text, profile)
            return InjectResult(True, method, time.monotonic() - started)
        except Exception as exc:
            log.warning("%s injection failed: %s", method, exc)
            # One retry on the other path — a dropped transcript is worse
            # than a clipboard we had to touch.
            other = "clipboard" if method == "wtype" else "wtype"
            try:
                if other == "wtype":
                    self._wtype(text)
                else:
                    self._clipboard(text, profile)
                return InjectResult(True, other, time.monotonic() - started,
                                    error=str(exc), fell_back=True)
            except Exception as exc2:
                return InjectResult(False, method, time.monotonic() - started, error=f"{exc} / {exc2}")

    # -- backends ----------------------------------------------------------

    def _wtype(self, text: str) -> None:
        if shutil.which("wtype") is None:
            raise RuntimeError("wtype is not installed")
        # Text goes in on stdin, not argv: no escaping, no ARG_MAX limit,
        # and text starting with '-' can't be read as a flag.
        argv = ["wtype"]
        if self.wtype_delay_ms:
            argv += ["-d", str(self.wtype_delay_ms)]
        argv.append("-")
        proc = subprocess.run(argv, input=text.encode(), capture_output=True, timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "wtype exited non-zero")

    def _clipboard(self, text: str, profile: dict[str, Any]) -> None:
        if shutil.which("wl-copy") is None:
            raise RuntimeError("wl-clipboard is not installed")

        saved = self._read_clipboard() if self.restore_after > 0 else None
        subprocess.run(["wl-copy", "--"], input=text.encode(), check=True, timeout=5)
        # Give the compositor a moment to publish the new selection before
        # the paste keystroke asks for it.
        time.sleep(self.paste_settle_ms / 1000.0)
        self._send_paste(str(profile.get("paste_key", self.default_paste_key)))

        if saved is not None:
            threading.Timer(self.restore_after, self._restore_clipboard, args=(saved,)).start()

    @staticmethod
    def _read_clipboard() -> bytes | None:
        if shutil.which("wl-paste") is None:
            return None
        try:
            proc = subprocess.run(
                ["wl-paste", "--no-newline"], capture_output=True, timeout=2
            )
            return proc.stdout if proc.returncode == 0 else b""
        except (subprocess.SubprocessError, OSError):
            return None

    @staticmethod
    def _restore_clipboard(saved: bytes) -> None:
        try:
            if saved:
                subprocess.run(["wl-copy", "--"], input=saved, timeout=5, check=False)
            else:
                subprocess.run(["wl-copy", "--clear"], timeout=5, check=False)
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("could not restore the clipboard: %s", exc)

    @staticmethod
    def _send_paste(combo: str) -> None:
        """Hyprland 0.56+ takes a Lua expression, not a bare dispatcher name."""
        parts = [p.strip().upper() for p in combo.split("+") if p.strip()]
        if not parts:
            raise ValueError(f"invalid paste shortcut {combo!r}")
        key, mods = parts[-1], parts[:-1]
        lua = (
            "hl.dsp.send_shortcut({{ mods = {mods!r}, key = {key!r}, window = 'activewindow' }})"
        ).format(mods=" ".join(mods), key=key).replace("'", '"')
        proc = subprocess.run(
            ["hyprctl", "dispatch", lua], capture_output=True, timeout=5
        )
        out = proc.stdout.decode("utf-8", "replace").strip()
        if proc.returncode != 0 or out != "ok":
            raise RuntimeError(f"hyprctl send_shortcut failed: {out or proc.stderr.decode()[:120]}")
