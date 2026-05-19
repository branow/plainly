"""CLI entrypoint for `score-bench`."""

from __future__ import annotations

import argparse
import sys

from ..core import RUNS_DIR
from .scorer import DEFAULT_MODEL, DEFAULT_W_COSINE, DEFAULT_W_LENGTH, Scorer, score_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a benchmark run vs ideal_answer.")
    parser.add_argument("ts", nargs="?", help="Run timestamp dir; default: latest")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--w-cosine", type=float, default=DEFAULT_W_COSINE)
    parser.add_argument("--w-length", type=float, default=DEFAULT_W_LENGTH)
    args = parser.parse_args()

    if args.ts:
        run_dir = RUNS_DIR / args.ts
    else:
        runs = sorted(d for d in RUNS_DIR.glob("*/") if d.is_dir())
        if not runs:
            print("No runs found.", file=sys.stderr)
            return 1
        run_dir = runs[-1]

    if not run_dir.exists():
        print(f"Run dir not found: {run_dir}", file=sys.stderr)
        return 1

    scorer = Scorer(args.model, args.w_cosine, args.w_length)
    print(f"Scoring {run_dir.name} with {args.model}", file=sys.stderr)
    out = score_run(run_dir, scorer)
    print(f"\nWrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
