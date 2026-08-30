"""LLM step interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class LlmResult:
    text: str
    model: str = ""
    backend: str = ""
    seconds: float = 0.0
    # Non-empty means the step did not produce usable text and the caller
    # must keep the text it already had.
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.text.strip())

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["seconds"] = round(self.seconds, 3)
        return data


class LlmBackend(Protocol):
    name: str

    def describe(self) -> str: ...

    def complete(self, system: str, text: str, *, timeout: float = 0.0) -> LlmResult: ...
