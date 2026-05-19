"""Anthropic API backend — direct SDK call with ANTHROPIC_API_KEY."""

from __future__ import annotations

import time

from anthropic import Anthropic

from .base import CallResult


# Aliases the Claude Code CLI accepts but the Anthropic API does not.
MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


class AnthropicBackend:
    name = "anthropic_api"

    def __init__(self) -> None:
        self.client = Anthropic()

    def call(self, system: str, user: str, model: str, max_tokens: int) -> CallResult:
        t0 = time.perf_counter()
        kwargs = {
            "model": MODEL_ALIASES.get(model, model),
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user}],
        }
        if system.strip():
            kwargs["system"] = system
        resp = self.client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        text = "".join(b.text for b in resp.content if b.type == "text")
        return CallResult(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_ms=latency_ms,
            stop_reason=resp.stop_reason,
        )
