"""score-bench feature: deterministic scoring + CLI."""

from .cli import main
from .scorer import Score, Scorer, load_scores, score_run

__all__ = ["main", "Score", "Scorer", "score_run", "load_scores"]
