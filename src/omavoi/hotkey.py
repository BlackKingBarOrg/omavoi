"""Global push-to-talk key, read straight from evdev.

Why not a Hyprland binding: binding press *and* release on a modifier key
fights itself — the modmask changes the instant the key goes down, which
immediately fires the release binding and yields a 0.0s recording. evdev
sits below xkb, so RIGHTALT is KEY_RIGHTALT no matter how the layout
remaps it (altwin:swap_alt_win included).

The devices are read passively, never grabbed, so the key still reaches
the focused application.
"""

from __future__ import annotations

import logging
import selectors
import threading
import time
from typing import Any, Callable

log = logging.getLogger(__name__)

_KEY_UP, _KEY_DOWN, _KEY_HOLD = 0, 1, 2


class HotkeyUnavailable(RuntimeError):
    pass


def key_code(name: str) -> int:
    from evdev import ecodes

    name = name.strip().upper()
    for candidate in (name, f"KEY_{name}"):
        code = getattr(ecodes, candidate, None)
        if isinstance(code, int):
            return code
    raise HotkeyUnavailable(f"unknown key name {name!r} (try RIGHTALT, F9, CAPSLOCK)")


def find_devices(code: int, explicit: list[str] | None = None) -> list[Any]:
    """Every readable device that can emit this key."""
    from evdev import InputDevice, ecodes, list_devices

    paths = explicit or list_devices()
    found = []
    for path in paths:
        try:
            dev = InputDevice(path)
        except (OSError, PermissionError):
            continue
        if code in dev.capabilities().get(ecodes.EV_KEY, []):
            found.append(dev)
        else:
            dev.close()
    return found


class HotkeyListener:
    """Calls on_press/on_release (push_to_talk) or on_toggle (toggle)."""

    def __init__(
        self,
        cfg: dict[str, Any],
        *,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        on_toggle: Callable[[], None],
    ) -> None:
        hk = cfg["hotkey"]
        self.key_name: str = hk["key"]
        self.code = key_code(self.key_name)
        self.mode: str = hk.get("mode", "push_to_talk")
        self.explicit: list[str] = list(hk.get("devices", []) or [])
        self.rescan_seconds = float(hk.get("rescan_seconds", 5.0))

        self._on_press = on_press
        self._on_release = on_release
        self._on_toggle = on_toggle

        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._devices: list[Any] = []
        self._held = False

    @property
    def device_names(self) -> list[str]:
        return [f"{d.path} {d.name}" for d in self._devices]

    def start(self) -> None:
        devices = find_devices(self.code, self.explicit or None)
        if not devices:
            raise HotkeyUnavailable(
                f"no readable device can emit {self.key_name}. Check that you are in the "
                "input group (`id -nG`); the group only takes effect on your next login."
            )
        self._devices = devices
        log.info("watching %s (%s) on: %s", self.key_name, self.mode, ", ".join(self.device_names))
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="omavoi-hotkey", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for dev in self._devices:
            try:
                dev.close()
            except Exception:
                pass
        self._devices = []

    def _loop(self) -> None:
        from evdev import ecodes

        sel = selectors.DefaultSelector()
        for dev in self._devices:
            sel.register(dev, selectors.EVENT_READ)
        last_scan = time.monotonic()

        while self._running.is_set():
            try:
                for key, _ in sel.select(timeout=0.5):
                    dev = key.fileobj
                    try:
                        for event in dev.read():  # type: ignore[union-attr]
                            if event.type == ecodes.EV_KEY and event.code == self.code:
                                self._handle(event.value)
                    except OSError:
                        # Keyboard unplugged or re-enumerated.
                        log.warning("input device went away: %s", getattr(dev, "path", dev))
                        sel.unregister(dev)
                        if dev in self._devices:
                            self._devices.remove(dev)  # type: ignore[arg-type]
                        if self._held:
                            self._held = False
                            self._safe(self._on_release)
            except Exception:
                log.exception("hotkey loop error")
                time.sleep(0.2)

            if time.monotonic() - last_scan > self.rescan_seconds:
                last_scan = time.monotonic()
                self._rescan(sel)

        sel.close()

    def _rescan(self, sel: selectors.BaseSelector) -> None:
        """Pick up a keyboard that was plugged in after we started."""
        known = {d.path for d in self._devices}
        for dev in find_devices(self.code, self.explicit or None):
            if dev.path in known:
                dev.close()
                continue
            log.info("new input device: %s %s", dev.path, dev.name)
            self._devices.append(dev)
            sel.register(dev, selectors.EVENT_READ)

    def _handle(self, value: int) -> None:
        if self.mode == "toggle":
            if value == _KEY_DOWN:
                self._safe(self._on_toggle)
            return

        if value == _KEY_DOWN and not self._held:
            self._held = True
            self._safe(self._on_press)
        elif value == _KEY_UP and self._held:
            self._held = False
            self._safe(self._on_release)
        # _KEY_HOLD (autorepeat) is ignored — it is not a new press.

    @staticmethod
    def _safe(fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception:
            log.exception("hotkey callback error")
