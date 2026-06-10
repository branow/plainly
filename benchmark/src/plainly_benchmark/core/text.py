"""Prose word counting, shared by the growth runner and the preview analysis.

Same definition as the plugin's measure hook: fenced and inline code are
stripped before counting, so code-heavy replies don't dominate.
"""

from __future__ import annotations

import re


def prose_words(text: str) -> int:
    text = re.sub(r"```[\s\S]*?```", " ", text or "")
    text = re.sub(r"`[^`]*`", " ", text)
    return len(text.split())
