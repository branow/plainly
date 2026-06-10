"""Conversation sessions for the growth benchmark.

Two ways to hold the same multi-turn conversation:

- ApiConversation — raw Anthropic API. The style text is the system prompt
  and the plainly refocus loop is emulated in-process (prompt-level test).
- ClaudeCodeConversation — a real Claude Code session via the Agent SDK with
  the actual plugin loaded, so its hooks (SessionStart inject, per-turn
  reminders, drift refocus) run natively (plugin-level test).
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from dataclasses import dataclass
from statistics import median

from anthropic import Anthropic

from ..core import ROOT, prose_words

# Mirrors the tuning knobs in scripts/refocus.mjs.
REFOCUS = {
    "min_replies": 6,
    "baseline_window": 3,
    "recent_window": 3,
    "drift_ratio": 1.6,
    "floor_words": 120,
    "cooldown": 5,
}

REMINDER_PATH = ROOT.parent / "prompt" / "reminder.md"

# The reminder's stable prefix — used to spot the real refocus hook firing
# inside a Claude Code session via the SDK's hook-event stream.
REMINDER_MARK = "[plainly]"


@dataclass
class Turn:
    sent: str  # what actually went out as the user message
    text: str
    input_tokens: int  # full context size of this request
    output_tokens: int
    latency_ms: int
    stop_reason: str | None
    reinjected: bool


class ApiConversation:
    """System prompt + in-process refocus emulation over messages.create."""

    def __init__(self, system: str, model: str, max_tokens: int) -> None:
        self.client = Anthropic()
        self.system = system
        self.model = model
        self.max_tokens = max_tokens
        self.messages: list[dict] = []
        # Baseline arms model "no plugin": no system prompt, no refocus loop.
        self.refocus = _Refocus() if system.strip() else None

    def send(self, user: str) -> Turn:
        reinjected = self.refocus.should_inject() if self.refocus else False
        sent = f"{REMINDER_PATH.read_text().strip()}\n\n{user}" if reinjected else user
        self.messages.append({"role": "user", "content": sent})

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self.messages,
        }
        if self.system.strip():
            kwargs["system"] = self.system

        t0 = time.perf_counter()
        resp = self.client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        text = "".join(b.text for b in resp.content if b.type == "text")
        self.messages.append({"role": "assistant", "content": text})
        if self.refocus:
            self.refocus.record(prose_words(text), nudged=reinjected)

        return Turn(
            sent=sent,
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_ms=latency_ms,
            stop_reason=resp.stop_reason,
            reinjected=reinjected,
        )

    def close(self) -> None:
        pass


class ClaudeCodeConversation:
    """One real Claude Code session, optionally with a plugin loaded.

    Tools are disabled and user/project settings are not loaded, so the only
    difference between arms is the plugin under test. The session keeps its
    own history; we only send the next user message each turn.
    """

    def __init__(self, plugin_dir: str | None, model: str) -> None:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        self._tmp = tempfile.TemporaryDirectory()
        options = ClaudeAgentOptions(
            allowed_tools=[],
            setting_sources=[],
            skills=None,
            plugins=[{"type": "local", "path": str(plugin_dir)}] if plugin_dir else [],
            permission_mode="default",
            model=model,
            cwd=self._tmp.name,
            include_partial_messages=False,
            include_hook_events=True,
        )
        self._loop = asyncio.new_event_loop()
        self._client = ClaudeSDKClient(options)
        self._loop.run_until_complete(self._client.connect())

    def send(self, user: str) -> Turn:
        return self._loop.run_until_complete(self._send(user))

    async def _send(self, user: str) -> Turn:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

        t0 = time.perf_counter()
        await self._client.query(user)

        text_parts: list[str] = []
        result: ResultMessage | None = None
        reinjected = False

        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                result = msg
            elif REMINDER_MARK in str(msg):
                # The plainly refocus hook fired on this prompt.
                reinjected = True
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if result is None:
            raise RuntimeError("claude SDK returned no ResultMessage")
        if result.is_error:
            err = (result.result or "").strip()[:500] or "unknown error"
            raise RuntimeError(f"claude SDK error: {err}")

        usage = result.usage or {}
        # input_tokens excludes the cached prefix; context size is the sum.
        context = (
            int(usage.get("input_tokens", 0))
            + int(usage.get("cache_creation_input_tokens", 0))
            + int(usage.get("cache_read_input_tokens", 0))
        )

        return Turn(
            sent=user,
            text="".join(text_parts) or (result.result or ""),
            input_tokens=context,
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_ms=result.duration_ms or latency_ms,
            stop_reason=result.stop_reason,
            reinjected=reinjected,
        )

    def close(self) -> None:
        try:
            self._loop.run_until_complete(self._client.disconnect())
        finally:
            self._loop.close()
            self._tmp.cleanup()


class _Refocus:
    """Per-arm drift state, evaluated on prompt submit like the real hook."""

    def __init__(self) -> None:
        self.counts: list[int] = []
        self.last_nudge_at = -999

    def should_inject(self) -> bool:
        k = REFOCUS
        if len(self.counts) < k["min_replies"]:
            return False
        if len(self.counts) - self.last_nudge_at < k["cooldown"]:
            return False
        baseline = median(self.counts[: k["baseline_window"]])
        recent = sum(self.counts[-k["recent_window"]:]) / k["recent_window"]
        return recent >= max(baseline * k["drift_ratio"], k["floor_words"])

    def record(self, words: int, *, nudged: bool) -> None:
        self.counts.append(words)
        if nudged:
            self.last_nudge_at = len(self.counts)
