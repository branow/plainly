"""Benchmark run loop. Iterates (prompt × style × sample), writes results.jsonl."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from ..backends.base import Backend
from ..core import Row, new_run_dir


def run(
    backend: Backend,
    prompts: dict[str, dict],
    styles: dict[str, str],
    *,
    model: str,
    samples: int,
    max_tokens: int,
) -> Path:
    if not prompts or not styles:
        raise RuntimeError("No prompts or styles selected.")

    ts, out_dir = new_run_dir()
    results_path = out_dir / "results.jsonl"
    meta_path = out_dir / "meta.json"

    meta = {
        "timestamp": ts,
        "backend": backend.name,
        "model": model,
        "samples": samples,
        "max_tokens": max_tokens,
        "prompts": [
            {"id": p["id"], "slug": p["slug"], "title": p["title"], "targets": p["targets"]}
            for p in prompts.values()
        ],
        "styles": list(styles),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    total = len(prompts) * len(styles) * samples
    i = 0
    with results_path.open("w") as f:
        for slug, p in prompts.items():
            for sid, stext in styles.items():
                for s in range(samples):
                    i += 1
                    print(f"[{i}/{total}] {p['id']:>2} {slug} x {sid} #{s}", file=sys.stderr)
                    try:
                        res = backend.call(stext, p["prompt"], model, max_tokens)
                    except Exception as e:
                        print(f"  error: {e}", file=sys.stderr)
                        continue
                    row = Row(
                        prompt_id=p["id"],
                        prompt_slug=slug,
                        prompt_title=p["title"],
                        prompt_targets=p["targets"],
                        style_id=sid,
                        sample=s,
                        backend=backend.name,
                        model=model,
                        input_tokens=res.input_tokens,
                        output_tokens=res.output_tokens,
                        latency_ms=res.latency_ms,
                        output=res.text,
                        stop_reason=res.stop_reason,
                    )
                    f.write(json.dumps(asdict(row)) + "\n")
                    f.flush()
    print(f"\nWrote {results_path}", file=sys.stderr)
    return results_path
