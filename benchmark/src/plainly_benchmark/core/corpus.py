"""Load prompts + style system-prompts from disk."""

from __future__ import annotations

import json
from pathlib import Path

from .paths import PROMPTS_DIR, STYLES_DIR


def load_prompts(d: Path = PROMPTS_DIR) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(d.glob("*.json")):
        obj = json.loads(p.read_text())
        obj["slug"] = p.stem
        out[p.stem] = obj
    return out


def load_styles(d: Path = STYLES_DIR) -> dict[str, str]:
    return {
        p.stem: p.read_text()
        for p in sorted(d.glob("*.md"))
        if p.stem.lower() != "readme"
    }


def filter_prompts(prompts: dict[str, dict], wanted: list[str]) -> dict[str, dict]:
    keep: dict[str, dict] = {}
    for w in wanted:
        if w.isdigit():
            i = int(w)
            for slug, obj in prompts.items():
                if obj["id"] == i:
                    keep[slug] = obj
        elif w in prompts:
            keep[w] = prompts[w]
    return keep
