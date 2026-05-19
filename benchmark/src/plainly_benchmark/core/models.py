"""Shared dataclasses for benchmark rows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Row:
    prompt_id: int
    prompt_slug: str
    prompt_title: str
    prompt_targets: list[str]
    style_id: str
    sample: int
    backend: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    output: str
    stop_reason: str | None
