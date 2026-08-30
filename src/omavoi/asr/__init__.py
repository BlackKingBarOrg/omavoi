"""ASR backend registry."""

from __future__ import annotations

from typing import Any

from .base import Backend, Segment, Transcript

__all__ = ["Backend", "Segment", "Transcript", "build", "BACKENDS"]

# name -> (aliases, one-line description)
BACKENDS: dict[str, tuple[tuple[str, ...], str]] = {
    "local-whisper": (
        ("local", "faster-whisper", "whisper", "ct2"),
        "faster-whisper / CTranslate2. NVIDIA CUDA only; fastest where it runs.",
    ),
    "local-whispercpp": (
        ("whispercpp", "whisper.cpp", "cpp", "vulkan"),
        "whisper.cpp. Vulkan covers NVIDIA, AMD and Intel, and it runs on CPU too.",
    ),
    "api": (
        ("openai", "remote"),
        "Any OpenAI-compatible endpoint: OpenAI, Groq, SiliconFlow, a local server.",
    ),
}

_ALIASES = {alias: name for name, (aliases, _) in BACKENDS.items() for alias in (name, *aliases)}


def canonical(name: str) -> str | None:
    return _ALIASES.get(str(name).strip().lower())


def build(cfg: dict[str, Any]) -> Backend:
    name = canonical(cfg["speech"]["backend"])
    if name == "local-whisper":
        from .local_whisper import LocalWhisperBackend

        return LocalWhisperBackend(cfg)
    if name == "local-whispercpp":
        from .local_whispercpp import WhisperCppBackend

        return WhisperCppBackend(cfg)
    if name == "api":
        from .api_whisper import ApiWhisperBackend

        return ApiWhisperBackend(cfg)
    raise ValueError(
        f"unknown speech.backend: {cfg['speech']['backend']!r} (one of: {', '.join(BACKENDS)})"
    )
