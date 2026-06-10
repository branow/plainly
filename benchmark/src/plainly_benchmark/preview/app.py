"""Flask app factory and route wiring."""

from __future__ import annotations

import re

from flask import Flask, Response, abort, jsonify, render_template

from ..core import load_prompts
from . import data, growth
from .report import build_report


_WS_SPLIT = re.compile(r"(\s+)")


def word_slice(text: str | None, n: int) -> tuple[str, str]:
    """Split text after the Nth word, preserving original whitespace.

    Returns (preview, rest). If text has <= n words, rest is "".
    """
    if not text:
        return "", ""
    parts = _WS_SPLIT.split(text)
    words = 0
    for i, p in enumerate(parts):
        if p and not p.isspace():
            words += 1
            if words > n:
                return "".join(parts[:i]), "".join(parts[i:])
    return text, ""


def word_count(text: str | None) -> int:
    if not text:
        return 0
    return sum(1 for p in _WS_SPLIT.split(text) if p and not p.isspace())


def create_app() -> Flask:
    app = Flask(__name__)
    app.jinja_env.filters["word_slice"] = word_slice
    app.jinja_env.filters["word_count"] = word_count

    @app.get("/")
    def index():
        return render_template("index.html", runs=data.list_runs())

    @app.get("/run/<ts>")
    def run_page(ts: str):
        run = data.load_run(ts)
        if run is None:
            abort(404)
        if isinstance(run, data.GrowthRun):
            return render_template(
                "growth_run.html",
                run=run,
                summary=growth.summarize(run.rows, run.meta.get("model", "?")),
                charts=growth.CHARTS,
                prose_words=growth.prose_words,
            )
        return render_template("run.html", run=run)

    @app.get("/run/<ts>/growth-chart/<name>.png")
    def growth_chart(ts: str, name: str):
        run = data.load_run(ts)
        if not isinstance(run, data.GrowthRun) or name not in growth.CHARTS:
            abort(404)
        return Response(growth.chart_png(run.rows, name), mimetype="image/png")

    @app.get("/report")
    def report_page():
        return render_template("report.html", report=build_report())

    @app.get("/prompts")
    def prompts_page():
        items = list(load_prompts().values())
        items.sort(key=lambda p: (p.get("id", 0), p.get("slug", "")))
        return render_template("prompts.html", prompts=items)

    @app.get("/api/state")
    def state():
        return jsonify({"mtime": data.runs_mtime()})

    return app
