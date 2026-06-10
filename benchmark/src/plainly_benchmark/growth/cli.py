"""CLI entrypoint for `growth-bench`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ..core import ROOT, load_styles
from .runner import run

CAVEMAN_FLAG = Path(
    os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")
) / ".caveman-active"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay one long conversation per arm. Inspect the results "
        "in the preview tool.",
        epilog="anthropic_api arms test style texts as system prompts "
        "(--style, refocus emulated). claude_code arms run real Claude Code "
        "sessions with the actual plugin loaded (--arm name=plugin_dir).",
    )
    parser.add_argument("--backend", default="anthropic_api",
                        choices=["anthropic_api", "claude_code"])
    parser.add_argument("--model", default="claude-opus-4-8")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument(
        "--style", default="plainly",
        help="anthropic_api: style id from styles/ to compare against the empty baseline",
    )
    parser.add_argument(
        "--arm", action="append", metavar="NAME[=PLUGIN_DIR]",
        help="claude_code: an arm to run; bare NAME = no plugin. Repeatable.",
    )
    parser.add_argument(
        "--append-to", metavar="TS",
        help="Add arms to an existing growth run (backend/model/max_tokens "
        "come from that run; no baseline rerun)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    if args.backend == "claude_code":
        arms = _claude_code_arms(args)
    else:
        arms = _api_arms(args)
    if arms is None:
        return 1

    flag_existed = CAVEMAN_FLAG.exists()
    try:
        run(
            arms,
            backend=args.backend,
            model=args.model,
            max_tokens=args.max_tokens,
            append_to=args.append_to,
        )
    finally:
        # The caveman plugin's SessionStart hook writes a mode flag into the
        # real config dir; don't leave it behind to affect the user's own
        # sessions.
        if not flag_existed and CAVEMAN_FLAG.exists():
            CAVEMAN_FLAG.unlink()

    print("Run `uv run preview` to see the analysis.", file=sys.stderr)
    return 0


def _api_arms(args) -> dict[str, dict] | None:
    styles = load_styles()
    if args.style not in styles:
        print(f"unknown style '{args.style}' (have: {', '.join(styles)})", file=sys.stderr)
        return None

    arms = {args.style: {"system": styles[args.style]}}
    if not args.append_to:
        arms = {"baseline": {"system": ""}, **arms}
    return arms


def _claude_code_arms(args) -> dict[str, dict] | None:
    if not args.arm:
        print("claude_code backend needs at least one --arm NAME[=PLUGIN_DIR]",
              file=sys.stderr)
        return None

    arms: dict[str, dict] = {}
    for spec in args.arm:
        name, _, plugin_dir = spec.partition("=")
        if plugin_dir:
            path = Path(plugin_dir).expanduser().resolve()
            if not (path / ".claude-plugin" / "plugin.json").exists():
                print(f"--arm {name}: no .claude-plugin/plugin.json under {path}",
                      file=sys.stderr)
                return None
            arms[name] = {"plugin_dir": str(path)}
        else:
            arms[name] = {"plugin_dir": None}
    return arms


if __name__ == "__main__":
    raise SystemExit(main())
