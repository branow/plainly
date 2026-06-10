"""Conversation-growth benchmark: plainly vs baseline over a long session.

Replays the same scripted multi-turn conversation twice — once with the
plainly style as the system prompt, once with the baseline — and records
how context size, token spend, and reply length grow turn by turn.
"""

from .cli import main

__all__ = ["main"]
