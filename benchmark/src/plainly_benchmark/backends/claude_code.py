"""Claude Code backend via the official Claude Agent SDK.

Uses the user's Claude Code subscription auth — no API key required.
Runs in a clean environment: `setting_sources=[]` disables user/project/local
settings (hooks, plugins, skills, output styles, statusline, auto-memory),
`allowed_tools=[]` blocks any tool use, and `cwd=` is a fresh temp dir so no
project `CLAUDE.md` or local memory can leak in.
"""

from __future__ import annotations

import asyncio
import tempfile
import time

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from .base import CallResult


class ClaudeCodeBackend:
    name = "claude_code"

    def call(self, system: str, user: str, model: str, max_tokens: int) -> CallResult:
        # max_tokens is not surfaced by the Claude Code SDK; the model's
        # default max_output_tokens is used.
        with tempfile.TemporaryDirectory() as tmp:
            return asyncio.run(self._call(system, user, model, tmp))

    async def _call(self, system: str, user: str, model: str, cwd: str) -> CallResult:
        options = ClaudeAgentOptions(
            system_prompt=system if system.strip() else None,
            allowed_tools=[],
            setting_sources=[],
            skills=None,
            plugins=[],
            permission_mode="default",
            model=model,
            cwd=cwd,
            include_partial_messages=False,
            include_hook_events=False,
        )

        text_parts: list[str] = []
        result: ResultMessage | None = None

        t0 = time.perf_counter()
        async for msg in query(prompt=user, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                result = msg
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if result is None:
            raise RuntimeError("claude SDK returned no ResultMessage")
        if result.is_error:
            err = (result.result or "").strip()[:500] or "unknown error"
            raise RuntimeError(f"claude SDK error: {err}")

        text = result.result if result.result is not None else "".join(text_parts)
        usage = result.usage or {}

        return CallResult(
            text=text,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_ms=result.duration_ms or latency_ms,
            stop_reason=result.stop_reason,
        )
