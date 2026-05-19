"""Backend protocol — one call, one result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class CallResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    stop_reason: str | None


class Backend(Protocol):
    name: str

    def call(self, system: str, user: str, model: str, max_tokens: int) -> CallResult: ...
