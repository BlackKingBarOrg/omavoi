"""A llama.cpp server that omavoi starts and owns.

The same arrangement as the speech engine: pick a model from the catalogue,
it downloads, and the daemon runs the server. Nothing to install beyond
`llama-cpp`, which reuses the ggml backends whisper.cpp already brought in.

The server is started lazily, on the first take that actually needs it. A
mode with no LLM step should cost no VRAM, and on a 16 GB card the speech
model and an 8B are already most of the budget.
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import time
from typing import Any

from .. import gpu, models
from .base import LlmResult

log = logging.getLogger(__name__)

_BINARIES = ("llama-server", "llama.cpp-server", "llamacpp-server")


def find_server() -> str | None:
    for name in _BINARIES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class LlamaLocalBackend:
    name = "llama-local"

    def __init__(self, name: str, cfg: dict[str, Any]) -> None:
        self.name = name
        self.backend = "llama-local"
        self.model_key = str(cfg.get("model", "") or "llm:qwen3-8b")
        self.binary = str(cfg.get("binary", "") or "")
        self.port = int(cfg.get("port", 0) or 0)
        self.gpu_layers = int(cfg.get("n_gpu_layers", 99))
        self.ctx_size = int(cfg.get("ctx_size", 4096))
        self.threads = int(cfg.get("threads", 0) or 0)
        self.startup_timeout = float(cfg.get("startup_timeout", 180.0))
        self.timeout = float(cfg.get("timeout", 60.0))
        self.max_tokens = int(cfg.get("max_tokens", 1024))
        self.temperature = float(cfg.get("temperature", 0.2))
        # Reasoning models think before answering, and a rewrite prompt gives
        # them nothing worth thinking about. Left on, Qwen3 spends the whole
        # token budget on a chain of thought and returns an empty string —
        # which reads downstream as a failed step and silently keeps the
        # untouched text. Off unless someone deliberately wants it.
        self.thinking = bool(cfg.get("thinking", False))

        self._proc: subprocess.Popen[bytes] | None = None
        self._client: Any = None
        self._url = ""
        self._fail = ""

    # -- lifecycle ---------------------------------------------------------

    def describe(self) -> str:
        state = "running" if self._proc and self._proc.poll() is None else "not started"
        return f"{self.name}: llama.cpp {self.model_key} ({state})"

    def _ensure(self) -> str:
        """Start the server if it is not up. Returns an error string, or ""."""
        if self._proc is not None and self._proc.poll() is None:
            return ""
        if self._fail:
            return self._fail

        binary = self.binary or find_server()
        if not binary:
            self._fail = ("llama-server is not installed. "
                          "On Arch/Omarchy: sudo pacman -S --needed llama-cpp")
            return self._fail

        path = models.local_path(self.model_key)
        if path is None:
            self._fail = (f"{self.model_key} is not downloaded. "
                          f"Run: omavoi model pull {self.model_key}")
            return self._fail

        # Check before spawning rather than letting llama.cpp discover it.
        # Its own failure is a multi-screen assertion, and by the time it
        # arrives the take has already fallen through with nothing to show
        # for it. Refusing here is a sentence the user can act on.
        #
        # Not cached in _fail: VRAM is shared with the desktop, so closing a
        # game should be enough to make the next take work.
        spec = models.spec(self.model_key)
        weights_mb = spec.size_mb if spec else int(path.stat().st_size / (1024 * 1024))
        check = gpu.fits(weights_mb, self.ctx_size, self.gpu_layers)
        if not check["fits"]:
            return gpu.explain_shortfall(check, self.model_key)

        import httpx

        port = self.port or _free_port()
        argv = [
            binary, "--model", str(path),
            "--host", "127.0.0.1", "--port", str(port),
            "--ctx-size", str(self.ctx_size),
            "--n-gpu-layers", str(self.gpu_layers),
            "--alias", self.model_key,
        ]
        if self.threads:
            argv += ["--threads", str(self.threads)]

        log.info("starting llama-server: %s", " ".join(argv))
        self._proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(os.environ)
        )
        self._url = f"http://127.0.0.1:{port}"
        self._client = httpx.Client(timeout=self.timeout)

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                out = b""
                if self._proc.stdout is not None:
                    out = self._proc.stdout.read() or b""
                self._fail = "llama-server exited on startup:\n" + _explain(out)
                return self._fail
            try:
                r = self._client.get(f"{self._url}/health", timeout=1.0)
                if r.status_code == 200:
                    log.info("llama-server ready at %s", self._url)
                    return ""
            except Exception:
                time.sleep(0.4)
        self._fail = f"llama-server was not ready within {self.startup_timeout:.0f}s"
        return self._fail

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)

    # -- inference ---------------------------------------------------------

    def complete(self, system: str, text: str, *, timeout: float = 0.0) -> LlmResult:
        started = time.monotonic()
        problem = self._ensure()
        if problem:
            return LlmResult("", self.model_key, self.backend,
                             time.monotonic() - started, error=problem)

        messages = []
        if system.strip():
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": text})

        try:
            response = self._client.post(
                f"{self._url}/v1/chat/completions",
                json={"model": self.model_key, "messages": messages,
                      "max_tokens": self.max_tokens, "temperature": self.temperature,
                      "stream": False,
                      # Ignored by models that have no thinking mode.
                      "chat_template_kwargs": {"enable_thinking": self.thinking}},
                timeout=timeout or self.timeout,
            )
            if response.status_code >= 400:
                return LlmResult("", self.model_key, self.backend,
                                 time.monotonic() - started,
                                 error=f"HTTP {response.status_code}: {response.text[:160]}")
            payload = response.json()
            content = str(payload["choices"][0]["message"]["content"]).strip()
            if not content:
                finish = (payload.get("choices") or [{}])[0].get("finish_reason", "")
                why = ("the model used its whole token budget without answering"
                       if finish == "length" else f"empty response ({finish or 'no reason'})")
                return LlmResult("", self.model_key, self.backend,
                                 time.monotonic() - started, error=why)
            return LlmResult(content, self.model_key, self.backend,
                             time.monotonic() - started)
        except Exception as exc:
            return LlmResult("", self.model_key, self.backend, time.monotonic() - started,
                             error=f"{type(exc).__name__}: {exc}")


def _explain(output: bytes) -> str:
    """The line that matters out of llama.cpp's startup noise."""
    lines = [l for l in output.decode("utf-8", "replace").splitlines() if l.strip()]
    for line in lines:
        low = line.lower()
        if "failed to fit" in low or ("out of" in low and "memory" in low):
            return (line + "\n  Not enough free VRAM. Either something else is holding "
                    "it — a second llama-server, or the speech model — or the weights "
                    "are too big. Lower llm.<name>.n_gpu_layers, or pick a smaller model.")
        if "error" in low or "failed" in low:
            return line
    return "\n".join(lines[-6:])
