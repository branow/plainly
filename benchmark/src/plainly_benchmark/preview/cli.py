"""CLI entrypoint for the preview server."""

from __future__ import annotations

import argparse

from ..core import RUNS_DIR
from .app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live preview server for plainly benchmark runs."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app()
    print(f"plainly preview → http://{args.host}:{args.port}")
    print(f"watching: {RUNS_DIR}")
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
