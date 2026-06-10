"""Growth run loop. Replays the conversation once per arm, writes results.jsonl.

Run dirs hold raw data only — same layout as bench runs (meta.json +
results.jsonl) with meta `type: "growth"`. Statistics and charts live in
the preview tool.

Two backends (see backends.py): `anthropic_api` tests the style text as a
system prompt with the refocus loop emulated; `claude_code` runs a real
Claude Code session per arm with the actual plugin loaded.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from ..core import RUNS_DIR, GrowthRow, new_run_dir
from .backends import ApiConversation, ClaudeCodeConversation


def run(
    arms: dict[str, dict],
    *,
    backend: str,
    model: str,
    max_tokens: int,
    append_to: str | None = None,
) -> Path:
    """Replay the conversation once per arm; return the results path.

    `arms` maps arm name -> {"system": str} for the anthropic_api backend or
    {"plugin_dir": str | None} for claude_code. With `append_to`, new arms
    are added to an existing growth run — backend, model and max_tokens come
    from that run's meta so arms stay comparable.
    """
    from .conversation import TURNS

    if append_to:
        out_dir = RUNS_DIR / append_to
        meta = json.loads((out_dir / "meta.json").read_text())
        if meta.get("type") != "growth":
            raise RuntimeError(f"{append_to} is not a growth run")
        backend = meta["backend"]
        model = meta["model"]
        max_tokens = meta["max_tokens"]
        meta["styles"] = list(dict.fromkeys(meta["styles"] + list(arms)))
        meta.setdefault("plugins", {}).update(_plugin_meta(arms))
        write_mode = "a"
    else:
        ts, out_dir = new_run_dir()
        meta = {
            "timestamp": ts,
            "type": "growth",
            "backend": backend,
            "model": model,
            "samples": 1,
            "max_tokens": max_tokens,
            "turns": len(TURNS),
            "styles": list(arms),
            "plugins": _plugin_meta(arms),
        }
        write_mode = "w"

    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    results_path = out_dir / "results.jsonl"
    with results_path.open(write_mode) as f:
        for name, spec in arms.items():
            print(f"[{name}] {len(TURNS)} turns on {model} via {backend}", file=sys.stderr)
            conversation = _open_conversation(backend, spec, model, max_tokens)
            try:
                for row in _run_arm(conversation, name, backend, model, TURNS):
                    f.write(json.dumps(asdict(row)) + "\n")
                    f.flush()
            finally:
                conversation.close()

    print(f"\nWrote {results_path}", file=sys.stderr)
    return results_path


def _open_conversation(backend: str, spec: dict, model: str, max_tokens: int):
    if backend == "claude_code":
        return ClaudeCodeConversation(spec.get("plugin_dir"), model)
    return ApiConversation(spec.get("system", ""), model, max_tokens)


def _run_arm(conversation, name: str, backend: str, model: str, turns: list[str]):
    for i, user in enumerate(turns, start=1):
        t = conversation.send(user)

        mark = "  [reinjected]" if t.reinjected else ""
        print(f"  turn {i:>2}: ctx {t.input_tokens:>6} tok, "
              f"reply {t.output_tokens:>5} tok{mark}",
              file=sys.stderr)

        yield GrowthRow(
            turn=i,
            user=t.sent,
            style_id=name,
            sample=0,
            backend=backend,
            model=model,
            input_tokens=t.input_tokens,
            output_tokens=t.output_tokens,
            latency_ms=t.latency_ms,
            output=t.text,
            stop_reason=t.stop_reason,
            reinjected=t.reinjected,
        )


def _plugin_meta(arms: dict[str, dict]) -> dict[str, str]:
    return {
        name: str(spec["plugin_dir"])
        for name, spec in arms.items()
        if spec.get("plugin_dir")
    }
