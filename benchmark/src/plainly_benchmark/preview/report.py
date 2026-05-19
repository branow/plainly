"""Cross-run aggregates for the /report page. Built fresh on each request."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from ..core import PROMPTS_DIR, RUNS_DIR
from . import data


@dataclass
class Bucket:
    """Running aggregate over a slice of rows."""

    n: int = 0
    n_scored: int = 0
    sum_combined: float = 0.0
    sum_cosine: float = 0.0
    sum_length_sim: float = 0.0
    sum_out_tokens: int = 0
    sum_latency_ms: int = 0

    def add(self, row: dict) -> None:
        self.n += 1
        self.sum_out_tokens += int(row.get("output_tokens", 0) or 0)
        self.sum_latency_ms += int(row.get("latency_ms", 0) or 0)
        if "combined" in row:
            self.n_scored += 1
            self.sum_combined += float(row["combined"])
            self.sum_cosine += float(row.get("cosine", 0.0))
            self.sum_length_sim += float(row.get("length_sim", 0.0))

    @property
    def avg_combined(self) -> float | None:
        return self.sum_combined / self.n_scored if self.n_scored else None

    @property
    def avg_cosine(self) -> float | None:
        return self.sum_cosine / self.n_scored if self.n_scored else None

    @property
    def avg_length_sim(self) -> float | None:
        return self.sum_length_sim / self.n_scored if self.n_scored else None

    @property
    def avg_out_tokens(self) -> float:
        return self.sum_out_tokens / self.n if self.n else 0.0

    @property
    def avg_latency_s(self) -> float:
        return (self.sum_latency_ms / self.n / 1000.0) if self.n else 0.0


@dataclass
class Report:
    n_runs: int
    n_rows: int
    styles: list[str]
    models: list[str]
    prompts: list[dict]  # [{slug, id, title}]
    by_style: dict[str, Bucket]
    by_model: dict[str, Bucket]
    by_style_model: dict[tuple[str, str], Bucket]
    by_prompt_style: dict[tuple[str, str], Bucket]
    style_ranking: list[tuple[str, Bucket]] = field(default_factory=list)


def _rank_styles(by_style: dict[str, Bucket]) -> list[tuple[str, Bucket]]:
    """Sort styles by avg_combined desc. Styles with no scored rows go last."""
    return sorted(
        by_style.items(),
        key=lambda kv: (
            kv[1].avg_combined is None,
            -(kv[1].avg_combined or 0.0),
            kv[0],
        ),
    )


def _iter_all_rows(runs_dir: Path = RUNS_DIR) -> list[dict]:
    """Stream every row from every run, score-merged."""
    out: list[dict] = []
    if not runs_dir.exists():
        return out
    for d in sorted(runs_dir.glob("*/")):
        if not (d / "meta.json").exists():
            continue
        rows = data._read_jsonl(d / "results.jsonl")
        scores = data._read_jsonl(d / "scores.jsonl")
        by_key = {(s["prompt_slug"], s["style_id"], s["sample"]): s for s in scores}
        for r in rows:
            s = by_key.get((r["prompt_slug"], r["style_id"], r["sample"]))
            if s:
                r["cosine"] = s["cosine"]
                r["length_sim"] = s["length_sim"]
                r["combined"] = s["combined"]
            out.append(r)
    return out


def build_report(
    runs_dir: Path = RUNS_DIR,
    prompts_dir: Path = PROMPTS_DIR,
) -> Report:
    rows = _iter_all_rows(runs_dir)

    by_style: dict[str, Bucket] = defaultdict(Bucket)
    by_model: dict[str, Bucket] = defaultdict(Bucket)
    by_style_model: dict[tuple[str, str], Bucket] = defaultdict(Bucket)
    by_prompt_style: dict[tuple[str, str], Bucket] = defaultdict(Bucket)

    styles: set[str] = set()
    models: set[str] = set()
    prompt_slugs: set[str] = set()

    for r in rows:
        sid = r["style_id"]
        model = r.get("model", "?")
        slug = r["prompt_slug"]

        styles.add(sid)
        models.add(model)
        prompt_slugs.add(slug)

        by_style[sid].add(r)
        by_model[model].add(r)
        by_style_model[(sid, model)].add(r)
        by_prompt_style[(slug, sid)].add(r)

    prompts: list[dict] = []
    for slug in sorted(prompt_slugs):
        path = prompts_dir / f"{slug}.json"
        if path.exists():
            obj = json.loads(path.read_text())
            prompts.append({"slug": slug, "id": obj.get("id", 0), "title": obj.get("title", slug)})
        else:
            prompts.append({"slug": slug, "id": 0, "title": slug})
    prompts.sort(key=lambda p: (p["id"], p["slug"]))

    n_runs = sum(
        1 for d in runs_dir.glob("*/") if (d / "meta.json").exists()
    ) if runs_dir.exists() else 0

    by_style_d = dict(by_style)
    return Report(
        n_runs=n_runs,
        n_rows=len(rows),
        styles=sorted(styles),
        models=sorted(models),
        prompts=prompts,
        by_style=by_style_d,
        by_model=dict(by_model),
        by_style_model=dict(by_style_model),
        by_prompt_style=dict(by_prompt_style),
        style_ranking=_rank_styles(by_style_d),
    )
