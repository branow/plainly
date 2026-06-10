"""Shared dataclasses for benchmark rows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GrowthRow:
    """One turn of the conversation-growth benchmark. Mirrors Row, with the
    prompt_* identity replaced by the turn number and the user message."""

    turn: int
    user: str
    style_id: str
    sample: int
    backend: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    output: str
    stop_reason: str | None
    reinjected: bool = False  # drift reminder was injected before this turn


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
