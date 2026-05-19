"""Factory: resolve a backend name to a constructed Backend instance."""

from __future__ import annotations

import os

from ..backends.base import Backend


def make_backend(name: str) -> Backend:
    if name == "claude_code":
        from ..backends.claude_code import ClaudeCodeBackend
        return ClaudeCodeBackend()
    if name == "anthropic_api":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not set; cannot use anthropic_api backend.")
        from ..backends.anthropic_api import AnthropicBackend
        return AnthropicBackend()
    raise SystemExit(f"Unknown backend: {name}")
