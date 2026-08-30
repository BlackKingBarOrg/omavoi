"""What the GPU is holding.

Keeping a speech model and an LLM resident at once is the whole point of the
daemon, and it is also the thing that quietly runs a card out of memory. The
number belongs on screen next to the buttons that add models.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def vram() -> dict[str, Any]:
    """Used and total VRAM in MB, or an empty dict when there is no NVIDIA GPU."""
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
        return {"name": name, "used_mb": int(used), "total_mb": int(total)}
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        return {}
