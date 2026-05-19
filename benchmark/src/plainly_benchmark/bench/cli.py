"""CLI entrypoint for `run-bench`."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from ..core import ROOT, filter_prompts, load_prompts, load_styles
from .backends import make_backend
from .runner import run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the benchmark across prompts × styles.")
    parser.add_argument("--backend", default="claude_code", choices=["claude_code", "anthropic_api"])
    parser.add_argument("--model", default="haiku", help="Model id or alias (haiku/sonnet/opus for claude_code)")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--prompts", nargs="*", help="Subset by id or slug")
    parser.add_argument("--styles", nargs="*", help="Subset of style ids")
    parser.add_argument("--score", action="store_true", help="Score results against ideal_answer after run")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    prompts = load_prompts()
    styles = load_styles()
    if args.prompts:
        prompts = filter_prompts(prompts, args.prompts)
    if args.styles:
        styles = {k: v for k, v in styles.items() if k in args.styles}

    backend = make_backend(args.backend)
    try:
        results_path = run(
            backend,
            prompts,
            styles,
            model=args.model,
            samples=args.samples,
            max_tokens=args.max_tokens,
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.score:
        from ..score import Scorer, score_run
        print("\nScoring...", file=sys.stderr)
        score_run(results_path.parent, Scorer())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
