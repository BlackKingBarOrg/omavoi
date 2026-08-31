"""What the GPU is holding, and whether the next model will fit.

Keeping a speech model and an LLM resident at once is the point of the
daemon, and it is also how a card quietly runs out. Checking before the
spawn is worth doing because the failure otherwise arrives as a llama.cpp
assertion several screens long, and the step then falls through silently.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Holder:
    pid: int
    name: str
    used_mb: int


def vram() -> dict[str, Any]:
    """Used and total VRAM in MB, or {} when there is no NVIDIA GPU."""
    if shutil.which("nvidia-smi") is None:
        return {}
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, timeout=3, check=False,
        )
        if out.returncode != 0:
            return {}
        line = out.stdout.decode().strip().splitlines()[0]
        name, used, total = (p.strip() for p in line.split(","))
        used_mb, total_mb = int(used), int(total)
        return {"name": name, "used_mb": used_mb, "total_mb": total_mb,
                "free_mb": max(0, total_mb - used_mb)}
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        return {}


def holders(limit: int = 3) -> list[Holder]:
    """The processes holding the most VRAM, biggest first.

    Naming them turns "not enough memory" into something the user can act
    on — it is usually one obvious program, not a mystery.
    """
    if shutil.which("nvidia-smi") is None:
        return []
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, timeout=3, check=False,
        )
        if out.returncode != 0:
            return []
        found: list[Holder] = []
        for line in out.stdout.decode().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3 or not parts[2].isdigit():
                continue
            # nvidia-smi prints the whole command line; the basename is enough
            # to recognise, and the full one is unreadable in a warning.
            name = parts[1].split()[0].rsplit("/", 1)[-1] if parts[1] else "?"
            found.append(Holder(int(parts[0]), name, int(parts[2])))
        found.sort(key=lambda h: -h.used_mb)
        return found[:limit]
    except (subprocess.SubprocessError, OSError, ValueError):
        return []


def needed_mb(weights_mb: int, ctx_size: int = 4096, gpu_layers: int = 99) -> int:
    """Roughly what a GGUF model will want on the GPU.

    Weights, plus a KV cache that grows with the context, plus a little for
    the runtime. Deliberately generous: refusing to start something that
    would have just fit is a smaller sin than evicting the speech model.
    """
    if gpu_layers <= 0:
        return 0
    kv_mb = max(128, int(ctx_size / 1024 * 160))
    return int(weights_mb * 1.03) + kv_mb + 256


def fits(weights_mb: int, ctx_size: int = 4096, gpu_layers: int = 99) -> dict[str, Any]:
    """Whether the model fits in what is free right now, and why not."""
    info = vram()
    want = needed_mb(weights_mb, ctx_size, gpu_layers)
    if not info:
        # No NVIDIA GPU to interrogate: do not block, the runtime will cope
        # or fail loudly on its own.
        return {"known": False, "fits": True, "needed_mb": want}
    free = int(info.get("free_mb", 0))
    ok = free >= want
    out: dict[str, Any] = {
        "known": True, "fits": ok, "needed_mb": want, "free_mb": free,
        "total_mb": info.get("total_mb", 0), "name": info.get("name", ""),
    }
    if not ok:
        out["holders"] = [{"pid": h.pid, "name": h.name, "used_mb": h.used_mb}
                          for h in holders()]
    return out


def explain_shortfall(check: dict[str, Any], model: str) -> str:
    """One line a user can act on."""
    free = check.get("free_mb", 0)
    want = check.get("needed_mb", 0)
    msg = (f"{model} needs about {want / 1024:.1f} GB of VRAM and only "
           f"{free / 1024:.1f} GB is free")
    top = check.get("holders") or []
    if top:
        who = ", ".join(f"{h['name']} {h['used_mb'] / 1024:.1f} GB" for h in top)
        msg += f". Currently held by: {who}"
    return msg
