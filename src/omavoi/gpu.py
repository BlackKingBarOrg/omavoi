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


def compute_apps() -> list[Holder]:
    """Every process nvidia-smi reports holding VRAM, biggest first."""
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
        return found
    except (subprocess.SubprocessError, OSError, ValueError):
        return []


def holders(limit: int = 3) -> list[Holder]:
    """The processes holding the most VRAM, biggest first.

    Naming them turns "not enough memory" into something the user can act
    on — it is usually one obvious program, not a mystery.
    """
    return compute_apps()[:limit]


def usage_by_pid() -> dict[int, int]:
    """VRAM per process, for attributing a bar to the models that hold it."""
    return {h.pid: h.used_mb for h in compute_apps()}


def segments(total_used_mb: int, speech_pid: int, llm_pids: set[int]) -> list[dict[str, Any]]:
    """Split the used VRAM into ours-for-speech, ours-for-LLM, and everything else.

    The remainder is computed rather than summed from the other processes:
    nvidia-smi's total includes memory no compute app claims (the display,
    mostly), and a stacked bar that does not add up to the number printed
    beside it is worse than one honest catch-all.
    """
    by_pid = usage_by_pid()
    speech_mb = by_pid.get(speech_pid, 0) if speech_pid else 0
    llm_mb = sum(by_pid.get(p, 0) for p in llm_pids)
    return [
        {"kind": "speech", "used_mb": speech_mb},
        {"kind": "llm", "used_mb": llm_mb},
        {"kind": "other", "used_mb": max(0, int(total_used_mb) - speech_mb - llm_mb)},
    ]


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


def fits_chain(wants: list[dict[str, Any]], live: set[str],
               reclaimable_mb: int = 0) -> dict[str, Any]:
    """Whether a whole chain of local models can be resident at once.

    A mode is speech plus zero or more LLM passes, and they all have to stay
    loaded together — swapping per take costs seconds. So the question that
    matters before switching modes is not "does this model fit" but "does
    everything this mode needs fit alongside what is already up".

    `wants` is [{"key", "weights_mb", "ctx_size", "gpu_layers"}]; anything in
    `live` is already resident and so already counted in used_mb.

    `reclaimable_mb` is memory the caller is about to release anyway — the
    local LLM of the mode being left. Counting it as free is the difference
    between "this mode does not fit" and "this mode does not fit beside a
    model that is on its way out".
    """
    info = vram()
    pending = [w for w in wants if w["key"] not in live]
    want = sum(needed_mb(int(w.get("weights_mb", 0)),
                         int(w.get("ctx_size", 4096)),
                         int(w.get("gpu_layers", 99))) for w in pending)
    out: dict[str, Any] = {
        "known": bool(info),
        "fits": True,
        "needed_mb": want,
        "pending": [w["key"] for w in pending],
    }
    if not info:
        # No NVIDIA GPU to interrogate: do not block. The runtime will cope or
        # fail loudly on its own, and guessing here would block a working setup.
        return out
    free = int(info.get("free_mb", 0))
    available = free + max(0, int(reclaimable_mb))
    out.update({"fits": want <= available, "free_mb": free,
                "reclaimable_mb": max(0, int(reclaimable_mb)),
                "available_mb": available,
                "total_mb": info.get("total_mb", 0), "name": info.get("name", "")})
    if not out["fits"]:
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
