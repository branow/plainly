"""Read-only access to runs/ on disk."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..core import PROMPTS_DIR, RUNS_DIR


@dataclass
class RunSummary:
    ts: str
    meta: dict
    n_rows: int
    expected: int


@dataclass
class Run:
    ts: str
    meta: dict
    rows: list[dict]
    grouped: dict[str, dict[str, list[dict]]]
    prompts: dict[str, dict]

    @property
    def styles(self) -> list[str]:
        return self.meta.get("styles", [])


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for _ in f)


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, skipping blank lines and rows the JSON parser can't
    handle. Stray NUL bytes (occasional partial-write artifact from the
    Claude Code CLI) are stripped before parsing. Bad lines are reported to
    stderr but never crash the caller."""
    if not path.exists():
        return []
    out: list[dict] = []
    for i, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.replace("\x00", "").strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"  warn: {path}:{i} skipped ({e})", file=sys.stderr)
    return out


def _expected_rows(meta: dict) -> int:
    return (
        len(meta.get("prompts", []))
        * len(meta.get("styles", []))
        * meta.get("samples", 1)
    )


def list_runs(runs_dir: Path = RUNS_DIR) -> list[RunSummary]:
    if not runs_dir.exists():
        return []
    out: list[RunSummary] = []
    for d in sorted(runs_dir.glob("*/"), reverse=True):
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        out.append(
            RunSummary(
                ts=d.name,
                meta=meta,
                n_rows=_count_lines(d / "results.jsonl"),
                expected=_expected_rows(meta),
            )
        )
    return out


def load_run(
    ts: str,
    runs_dir: Path = RUNS_DIR,
    prompts_dir: Path = PROMPTS_DIR,
) -> Run | None:
    d = runs_dir / ts
    meta_path = d / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    rows = _read_jsonl(d / "results.jsonl")

    scores = _read_jsonl(d / "scores.jsonl")
    by_key = {(s["prompt_slug"], s["style_id"], s["sample"]): s for s in scores}
    for r in rows:
        s = by_key.get((r["prompt_slug"], r["style_id"], r["sample"]))
        if s:
            r["cosine"] = s["cosine"]
            r["length_sim"] = s["length_sim"]
            r["combined"] = s["combined"]
            r["response_words"] = s["response_words"]
            r["ideal_words"] = s["ideal_words"]

    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[r["prompt_slug"]][r["style_id"]].append(r)

    prompts: dict[str, dict] = {}
    for p in meta.get("prompts", []):
        path = prompts_dir / f"{p['slug']}.json"
        if path.exists():
            prompts[p["slug"]] = json.loads(path.read_text())

    return Run(ts=ts, meta=meta, rows=rows, grouped=grouped, prompts=prompts)


def runs_mtime(runs_dir: Path = RUNS_DIR) -> float:
    if not runs_dir.exists():
        return 0.0
    latest = 0.0
    for p in runs_dir.rglob("*"):
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        if mt > latest:
            latest = mt
    return latest
