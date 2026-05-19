"""Deterministic scoring: semantic similarity + length similarity vs ideal_answer.

Two signals, combined 70/30 by default:
  - `cosine` — embedding cosine similarity (sentence-transformers, local model)
  - `length_sim` — tolerance-banded length match. Within tolerance band
    `max(20, 0.2 * i_words)`: 1.0. Beyond: linear decay against floored
    denominator `max(i_words, 50)`. Short ideals get forgiven on small
    absolute deltas (23->50 isn't punished like 600->1400).

`combined = 0.7 * cosine + 0.3 * length_sim`

Scores stored per-row in `runs/<ts>/scores.jsonl`. Merge key:
  (prompt_slug, style_id, sample).
"""

from __future__ import annotations

import os

# Silence Hugging Face hub + transformers chatter before any of those imports.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

from ..core import load_prompts


# Default cheap model. ~90MB download on first use, ~80ms / pair on CPU.
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_W_COSINE = 0.7
DEFAULT_W_LENGTH = 0.3


@dataclass
class Score:
    prompt_slug: str
    style_id: str
    sample: int
    cosine: float
    length_sim: float
    combined: float
    response_words: int
    ideal_words: int


class Scorer:
    """Lazy-load the embedding model; reuse across calls."""

    def __init__(self, model_name: str = DEFAULT_MODEL,
                 w_cosine: float = DEFAULT_W_COSINE,
                 w_length: float = DEFAULT_W_LENGTH) -> None:
        self.model_name = model_name
        self.w_cosine = w_cosine
        self.w_length = w_length
        self._model = None

    def _load(self):
        if self._model is None:
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
        return self._model

    def score_one(self, response: str, ideal: str, *,
                  prompt_slug: str, style_id: str, sample: int) -> Score:
        model = self._load()
        emb_r, emb_i = model.encode([response, ideal], normalize_embeddings=True)
        cosine = float((emb_r * emb_i).sum())  # dot of normalized = cosine

        r_words = len(response.split())
        i_words = max(len(ideal.split()), 1)
        # Tolerance band: small absolute differences are forgiven; a 23->50 gap
        # shouldn't score the same as a 600->1400 gap. Within tolerance: 1.0.
        # Beyond: linear decay against a floored denominator so short ideals
        # don't get crushed.
        tolerance = max(20, 0.2 * i_words)
        denom = max(i_words, 50)
        excess = max(0.0, abs(r_words - i_words) - tolerance)
        length_sim = max(0.0, 1.0 - excess / denom)

        combined = self.w_cosine * cosine + self.w_length * length_sim
        return Score(
            prompt_slug=prompt_slug,
            style_id=style_id,
            sample=sample,
            cosine=round(cosine, 4),
            length_sim=round(length_sim, 4),
            combined=round(combined, 4),
            response_words=r_words,
            ideal_words=i_words,
        )


def score_run(run_dir: Path, scorer: Scorer | None = None) -> Path:
    """Read runs/<ts>/results.jsonl, write runs/<ts>/scores.jsonl. Returns scores path."""
    results_path = run_dir / "results.jsonl"
    scores_path = run_dir / "scores.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(results_path)

    prompts = load_prompts()
    scorer = scorer or Scorer()

    n = 0
    with results_path.open() as inp, scores_path.open("w") as out:
        for i, raw in enumerate(inp, 1):
            line = raw.replace("\x00", "").strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  warn: {results_path.name}:{i} skipped ({e})", file=sys.stderr)
                continue
            slug = r["prompt_slug"]
            ideal = (prompts.get(slug) or {}).get("ideal_answer", "")
            if not ideal:
                print(f"  skip {slug}: no ideal_answer", file=sys.stderr)
                continue
            s = scorer.score_one(
                r["output"], ideal,
                prompt_slug=slug,
                style_id=r["style_id"],
                sample=r["sample"],
            )
            out.write(json.dumps(asdict(s)) + "\n")
            out.flush()
            n += 1
            print(f"  [{n}] {slug} x {r['style_id']} #{r['sample']}: "
                  f"cos={s.cosine:.3f} len={s.length_sim:.3f} → {s.combined:.3f}",
                  file=sys.stderr)
    return scores_path


def load_scores(run_dir: Path) -> dict[tuple[str, str, int], dict]:
    """Merge key: (prompt_slug, style_id, sample) -> score dict."""
    p = run_dir / "scores.jsonl"
    if not p.exists():
        return {}
    out: dict[tuple[str, str, int], dict] = {}
    for i, raw in enumerate(p.read_text().splitlines(), 1):
        line = raw.replace("\x00", "").strip()
        if not line:
            continue
        try:
            s = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  warn: {p.name}:{i} skipped ({e})", file=sys.stderr)
            continue
        out[(s["prompt_slug"], s["style_id"], s["sample"])] = s
    return out
