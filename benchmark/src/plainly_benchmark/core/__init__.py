"""Shared primitives: paths, dataclasses, corpus loaders, run-dir helpers.

Re-exported flat so callers can do `from plainly_benchmark.core import X`.
"""

from .corpus import filter_prompts, load_prompts, load_styles
from .models import Row
from .paths import PROMPTS_DIR, ROOT, RUNS_DIR, STYLES_DIR
from .runs import new_run_dir

__all__ = [
    "ROOT",
    "PROMPTS_DIR",
    "STYLES_DIR",
    "RUNS_DIR",
    "Row",
    "load_prompts",
    "load_styles",
    "filter_prompts",
    "new_run_dir",
]
