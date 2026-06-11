"""Sanity check the scoring formula on hand-written response variants.

For each JSON file in `tests/data/score_variants/`, load the prompt by id,
score each variant against the prompt's `ideal_answer`, and print a ranked
table. Run with `-s` to see the table.

  uv run pytest tests/test_scoring.py -s

To add a new case: drop a new `prompt_<id>.json` in that directory with
`{ prompt_id, variants: [{label, text}, ...] }`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plainly_benchmark.core import load_prompts
from plainly_benchmark.score import Scorer


DATA_DIR = Path(__file__).parent / "data" / "score_variants"


def _variant_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("prompt_*.json"))


@pytest.fixture(scope="module")
def scorer() -> Scorer:
    return Scorer()


@pytest.fixture(scope="module")
def prompts_by_id() -> dict[int, dict]:
    return {p["id"]: p for p in load_prompts().values()}


@pytest.mark.parametrize(
    "data_file",
    _variant_files(),
    ids=lambda p: p.stem,
)
def test_score_variants(data_file: Path, scorer: Scorer, prompts_by_id: dict[int, dict]) -> None:
    case = json.loads(data_file.read_text())
    pid = case["prompt_id"]
    prompt = prompts_by_id.get(pid)
    if prompt is None:
        pytest.skip(f"prompt id {pid} not in corpus")

    ideal = prompt.get("ideal_answer", "")
    assert ideal, f"prompt #{pid} has no ideal_answer"

    variants = case["variants"]
    assert variants, "no variants in data file"

    scored = []
    for v in variants:
        s = scorer.score_one(
            v["text"], ideal,
            prompt_slug=prompt.get("slug", "?"),
            style_id=f"variant-{v['label']}",
            sample=0,
        )
        scored.append((v["label"], s))

    scored.sort(key=lambda r: r[1].combined, reverse=True)

    print()
    print(f"prompt #{pid}: {prompt['title']}\n")
    print(f"{'rank':>4}  {'variant':>18}  {'words':>5}  {'cosine':>6}  {'lensim':>6}  {'COMBINED':>9}")
    print("-" * 70)
    for rank, (label, s) in enumerate(scored, 1):
        print(f"{rank:>4}  {label:>18}  {s.response_words:>5}  "
              f"{s.cosine:>6.3f}  {s.length_sim:>6.3f}  {s.combined:>9.3f}")
    print()

    # Loose sanity bounds.
    for label, s in scored:
        assert s.cosine > 0.5, f"variant {label} cosine too low: {s.cosine}"
        assert 0 <= s.combined <= 1.0


def test_length_sim_forgives_small_absolute_excess(scorer: Scorer) -> None:
    # ideal=5 words → tolerance=max(20, 0.2*5)=20, so a 20-word response
    # (delta 15) sits inside the band and is not penalized.
    ideal = "one two three four five"
    response = " ".join(["x"] * 20)
    s = scorer.score_one(response, ideal, prompt_slug="t", style_id="t", sample=0)
    assert s.length_sim == 1.0


def test_length_sim_clamps_to_zero_when_response_far_exceeds_ideal(scorer: Scorer) -> None:
    # ideal=5 words → tolerance=20, denom=50: excess hits the denominator
    # at delta>=70 words, so a 100-word response clamps to 0.
    ideal = "one two three four five"
    response = " ".join(["x"] * 100)
    s = scorer.score_one(response, ideal, prompt_slug="t", style_id="t", sample=0)
    assert s.length_sim == 0.0


def test_length_sim_one_when_equal_word_count(scorer: Scorer) -> None:
    ideal = "alpha beta gamma delta"
    response = "alpha beta gamma delta"
    s = scorer.score_one(response, ideal, prompt_slug="t", style_id="t", sample=0)
    assert s.length_sim == 1.0
    assert s.cosine == pytest.approx(1.0, abs=1e-3)
