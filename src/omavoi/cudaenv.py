"""Make CTranslate2 find cuBLAS/cuDNN without the user exporting LD_LIBRARY_PATH.

Omarchy ships no system CUDA toolkit, so the runtime libs come from the
nvidia-*-cu12 pip wheels. CTranslate2 dlopen()s them by soname, which only
succeeds if they are already resolved in the process — and editing
os.environ["LD_LIBRARY_PATH"] does not help, because glibc snapshots that
at process start. So we dlopen every wheel-provided .so by absolute path
with RTLD_GLOBAL, which also satisfies libcudnn's own internal dlopens.
"""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# cuBLAS first: cuDNN links against it.
_WHEEL_PACKAGES = ["nvidia.cublas.lib", "nvidia.cuda_nvrtc.lib", "nvidia.cudnn.lib"]

_result: dict[str, object] | None = None


def _package_dir(module: str) -> Path | None:
    try:
        mod = __import__(module, fromlist=["__path__"])
    except ImportError:
        return None
    # These are namespace packages, so __file__ is None — use __path__.
    file = getattr(mod, "__file__", None)
    if file:
        return Path(file).parent
    paths = list(getattr(mod, "__path__", []) or [])
    return Path(paths[0]) if paths else None


def library_dirs() -> list[Path]:
    return [d for d in (_package_dir(p) for p in _WHEEL_PACKAGES) if d is not None]


def preload() -> dict[str, object]:
    """dlopen the wheel CUDA libs into this process. Idempotent."""
    global _result
    if _result is not None:
        return _result

    dirs = library_dirs()
    pending: list[Path] = []
    for directory in dirs:
        pending.extend(sorted(p for p in directory.glob("*.so*") if p.is_file()))

    loaded: list[str] = []
    failed: dict[str, str] = {}
    # Several passes: inter-library dependencies resolve in whatever order.
    for _ in range(3):
        if not pending:
            break
        retry: list[Path] = []
        for path in pending:
            try:
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
                loaded.append(path.name)
                failed.pop(path.name, None)
            except OSError as exc:
                failed[path.name] = str(exc)
                retry.append(path)
        if len(retry) == len(pending):
            break
        pending = retry

    _result = {
        "dirs": [str(d) for d in dirs],
        "loaded": loaded,
        "failed": failed,
    }
    if loaded:
        log.debug("preloaded %d CUDA libs from wheels", len(loaded))
    if failed:
        log.debug("could not preload: %s", ", ".join(failed))
    return _result


def diagnose() -> dict[str, object]:
    """What `omavoi doctor` reports about the CUDA stack."""
    pre = preload()
    info: dict[str, object] = {
        "wheel_lib_dirs": pre["dirs"],
        "preloaded_count": len(pre["loaded"]),  # type: ignore[arg-type]
        "preload_failures": pre["failed"],
        "system_cuda": bool(
            os.path.exists("/opt/cuda") or os.path.exists("/usr/lib/libcublas.so.12")
        ),
    }
    try:
        import ctranslate2

        info["ctranslate2"] = ctranslate2.__version__
        info["cuda_devices"] = ctranslate2.get_cuda_device_count()
        if ctranslate2.get_cuda_device_count():
            info["cuda_compute_types"] = sorted(ctranslate2.get_supported_compute_types("cuda"))
    except Exception as exc:
        info["ctranslate2_error"] = str(exc)
    return info
