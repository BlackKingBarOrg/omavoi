"""LLM backends, referenced from a mode's chain by name."""

from __future__ import annotations

import logging
from typing import Any

from .base import LlmBackend, LlmResult

log = logging.getLogger(__name__)

__all__ = ["LlmBackend", "LlmResult", "Registry", "BACKENDS"]

BACKENDS: dict[str, str] = {
    "llama-cpp": "A local llama.cpp / ollama / vLLM server speaking the OpenAI API.",
    "openai": "OpenAI, or anything else OpenAI-compatible.",
    "anthropic": "The Claude API.",
}


def _build_one(name: str, cfg: dict[str, Any]) -> LlmBackend:
    backend = str(cfg.get("backend", "openai")).strip().lower()
    if backend == "anthropic":
        from .anthropic import AnthropicBackend

        return AnthropicBackend(name, cfg)
    if backend in ("llama-cpp", "llama.cpp", "openai", "openai-compatible", "ollama", "vllm"):
        from .openai_compat import OpenAiCompatBackend

        return OpenAiCompatBackend(name, cfg)
    raise ValueError(f"unknown llm.{name}.backend: {backend!r} (one of: {', '.join(BACKENDS)})")


class Registry:
    """Lazily builds the LLM clients a mode's chain actually names."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._defs: dict[str, Any] = dict(cfg.get("llm", {}))
        self._built: dict[str, LlmBackend] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._defs

    def names(self) -> list[str]:
        return sorted(self._defs)

    def get(self, name: str) -> LlmBackend | None:
        if name in self._built:
            return self._built[name]
        cfg = self._defs.get(name)
        if cfg is None:
            log.warning("no [llm.%s] defined", name)
            return None
        try:
            backend = _build_one(name, cfg)
        except Exception as exc:
            log.error("could not build llm %r: %s", name, exc)
            return None
        self._built[name] = backend
        return backend
