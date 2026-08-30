"""What is still missing before dictation works, and how to fix each thing.

Both `omavoi setup` and the plugin's first-run screen read from here, so the
two never disagree about what is done. Nothing runs on its own: a step is
either already satisfied, or it hands back the exact command it would run.
"""

from __future__ import annotations

import grp
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from . import models, paths


@dataclass(slots=True)
class Step:
    key: str
    title: str
    done: bool
    detail: str = ""
    command: str = ""
    needs_root: bool = False
    # A step that can be skipped without blocking dictation.
    optional: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "title": self.title, "done": self.done,
            "detail": self.detail, "command": self.command,
            "needs_root": self.needs_root, "optional": self.optional, "note": self.note,
        }


@dataclass(slots=True)
class Report:
    steps: list[Step] = field(default_factory=list)

    @property
    def done(self) -> int:
        return sum(1 for s in self.steps if s.done)

    @property
    def blocking(self) -> list[Step]:
        return [s for s in self.steps if not s.done and not s.optional]

    @property
    def ready(self) -> bool:
        return not self.blocking

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "done": self.done,
            "total": len(self.steps),
            "steps": [s.as_dict() for s in self.steps],
        }


def _ggml_backends() -> list[str]:
    """Which ggml compute plugins are installed. Arch ships one package each."""
    from pathlib import Path

    out: list[str] = []
    for directory in (Path("/usr/lib/ggml"), Path("/usr/lib64/ggml")):
        if directory.is_dir():
            out.extend(p.name for p in directory.glob("libggml-*.so*"))
    return out


def _in_input_group() -> bool:
    try:
        gid = grp.getgrnam("input").gr_gid
    except KeyError:
        return False
    return gid in os.getgroups()


def _unit_active() -> bool:
    if shutil.which("systemctl") is None:
        return False
    try:
        out = subprocess.run(
            ["systemctl", "--user", "is-enabled", "omavoid.service"],
            capture_output=True, timeout=3, check=False,
        )
        return out.stdout.decode().strip() in ("enabled", "static", "linked")
    except (subprocess.SubprocessError, OSError):
        return False


def check(cfg: dict[str, Any]) -> Report:
    from . import asr
    from .asr.local_whispercpp import find_server

    steps: list[Step] = []
    backend = asr.canonical(cfg["speech"]["backend"]) or ""

    # 1. What we type with. Omarchy ships all of these, so this is normally green.
    missing = [t for t in ("pw-record", "wtype", "wl-copy", "hyprctl") if not shutil.which(t)]
    steps.append(Step(
        "tools", "Typing and audio tools", not missing,
        detail="pw-record, wtype, wl-clipboard, hyprctl"
        if not missing else "missing: " + ", ".join(missing),
        command="sudo pacman -S --needed pipewire wtype wl-clipboard" if missing else "",
        needs_root=bool(missing),
    ))

    # 2. The speech engine, which depends on which backend is selected.
    if backend == "local-whispercpp":
        server = find_server()
        # ggml loads its compute backends as plugins, and whisper still asks
        # for a CPU device for the tensors it does not offload. With only the
        # GPU plugin installed it aborts on GGML_ASSERT(device) part-way
        # through loading the model — so check for both, or the failure is a
        # core dump with no clue in it.
        backends = _ggml_backends()
        has_cpu = any("cpu" in b for b in backends)
        has_gpu = any(b.split("libggml-")[-1].split(".")[0] in
                      ("vulkan", "cuda", "hip", "sycl", "metal") for b in backends)
        ok = bool(server) and has_cpu
        if not server:
            detail = "whisper.cpp is not installed"
        elif not has_cpu:
            detail = ("whisper.cpp is installed but no CPU ggml backend is — "
                      "it will abort while loading the model")
        else:
            detail = f"{server}, backends: {', '.join(sorted(backends)) or 'none'}"
        steps.append(Step(
            "engine", "Speech engine (Vulkan)", ok,
            detail=detail,
            command="sudo pacman -S --needed whisper-cpp ggml-cpu ggml-vulkan",
            needs_root=True,
            note="About 10 MB. ggml-cpu is not optional: the GPU plugin alone "
                 "cannot satisfy whisper's CPU tensors."
                 + ("" if has_gpu else " Swap ggml-vulkan for ggml-cuda or "
                    "ggml-hip if you would rather use the vendor backend."),
        ))
    elif backend == "local-whisper":
        try:
            import ctranslate2  # noqa: F401

            ok, detail = True, "ctranslate2 with the CUDA runtime wheels"
        except ImportError:
            ok, detail = False, "ctranslate2 is not installed"
        steps.append(Step(
            "engine", "Speech engine (CUDA)", ok, detail=detail,
            command="uv tool install 'omavoi[cuda]'",
            note="About 2.2 GB of NVIDIA wheels. Roughly twice as fast as Vulkan.",
        ))
    else:
        steps.append(Step("engine", "Speech engine (remote API)", True,
                          detail=f"provider {cfg['speech']['api'].get('provider', '?')}"))

    # 3. Weights. Never shipped: far too large for a package or a plugin repo.
    key = cfg["speech"]["model"]
    have = models.is_downloaded(key)
    spec = models.spec(key)
    size = f"{spec.size_mb / 1024:.1f} GB" if spec else "unknown size"
    steps.append(Step(
        "model", f"Model weights ({key})", have,
        detail=str(models.local_path(key)) if have else f"not downloaded, {size}",
        command=f"omavoi model pull {key}",
    ))

    # 4. The hotkey. This is the one step that cannot be finished in place.
    group = _in_input_group()
    steps.append(Step(
        "hotkey", f"Hotkey ({cfg['hotkey']['key']} via evdev)", group,
        detail="in the input group" if group else "not in the input group",
        command="sudo usermod -aG input $USER",
        needs_root=True,
        optional=True,
        note="The group only takes effect at your next login. Until then, bind a "
             "non-modifier key such as F9 in Hyprland — modifier keys cannot be "
             "bound that way, because pressing one fires the release binding at once.",
    ))

    # 5. Run it at login.
    steps.append(Step(
        "service", "Start at login", _unit_active(),
        detail="omavoid.service is enabled" if _unit_active() else "not enabled",
        command="systemctl --user enable --now omavoid.service",
        optional=True,
    ))
    return Report(steps)


def config_written() -> bool:
    return paths.config_file().exists()
