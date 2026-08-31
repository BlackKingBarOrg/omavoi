"""LLM backends, referenced from a mode's chain by name."""

from __future__ import annotations

import logging
from typing import Any

from .base import LlmBackend, LlmResult

log = logging.getLogger(__name__)

__all__ = ["LlmBackend", "LlmResult", "Registry", "BACKENDS", "ON_MACHINE"]

BACKENDS: dict[str, str] = {
    "llama-cpp": "A local llama.cpp / ollama / vLLM server speaking the OpenAI API.",
    "openai": "OpenAI, or anything else OpenAI-compatible.",
    "anthropic": "The Claude API.",
    "llama-local": "A llama.cpp server omavoi starts and owns, with its models "
                   "in the same catalogue as the speech ones.",
    "claude-cli": "The Claude Code CLI already logged in on this machine. No key "
                  "needed; costs several seconds of startup per take.",
}


# Backends whose weights run here, so using them sends nothing off the
# machine. Kept beside BACKENDS because the UI badges every LLM with this and
# a new backend added below but not listed here would badge itself "remote".
# claude-cli is deliberately absent: the process is local, the inference is not.
ON_MACHINE: frozenset[str] = frozenset({
    "llama-cpp", "llama.cpp", "llamacpp", "llama-local", "ollama", "vllm",
})


def _build_one(name: str, cfg: dict[str, Any]) -> LlmBackend:
    backend = str(cfg.get("backend", "openai")).strip().lower()
    if backend in ("llama-local", "llama.cpp", "llamacpp"):
        from .llama_local import LlamaLocalBackend

        return LlamaLocalBackend(name, cfg)
    if backend in ("claude-cli", "claude-code", "claude"):
        from .claude_cli import ClaudeCliBackend

        return ClaudeCliBackend(name, cfg)
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
        self._why: dict[str, str] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._defs

    def names(self) -> list[str]:
        return sorted(self._defs)

    def close(self) -> None:
        """Stop anything this registry started. Called when the daemon exits."""
        for backend in self._built.values():
            stop = getattr(backend, "close", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    log.debug("could not stop %s", getattr(backend, "name", backend))

    def why(self, name: str) -> str:
        """Why `get` returned None, for the warning the user actually sees."""
        return self._why.get(name, "not configured")

    def get(self, name: str) -> LlmBackend | None:
        if name in self._built:
            return self._built[name]
        cfg = self._defs.get(name)
        if cfg is None:
            log.warning("no [llm.%s] defined", name)
            self._why[name] = f"no [llm.{name}] in the config"
            return None
        try:
            backend = _build_one(name, cfg)
        except Exception as exc:
            # A backend name the running daemon does not know reads exactly
            # like a missing entry unless it says so — and after an upgrade
            # that adds one, the daemon needs restarting, not reloading.
            log.error("could not build llm %r: %s", name, exc)
            self._why[name] = str(exc)
            return None
        self._built[name] = backend
        return backend
