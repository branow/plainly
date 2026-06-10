"""Statistics and charts for growth runs, computed from raw rows on demand."""

from __future__ import annotations

import io
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..core import prose_words

# $/MTok (input, output) — cost estimates in the summary table.
PRICES = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

CHARTS = ("context-growth", "reply-length")

STYLE_COLORS = {"baseline": "#c0392b", "plainly": "#2471a3", "caveman": "#1e8449"}
FALLBACK_COLORS = ["#7d3c98", "#1e8449", "#b7950b"]


def by_style(rows: list[dict]) -> dict[str, list[dict]]:
    """Group rows by style_id, ordered by turn."""
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        out[r["style_id"]].append(r)
    for series in out.values():
        series.sort(key=lambda r: r["turn"])
    return dict(out)


def summarize(rows: list[dict], model: str) -> dict[str, dict]:
    """Per-style totals: tokens, prose words, latency, and estimated cost."""
    out: dict[str, dict] = {}
    for sid, series in by_style(rows).items():
        words = [prose_words(r["output"]) for r in series]
        s = {
            "turns": len(series),
            "input_tokens": sum(r["input_tokens"] for r in series),
            "output_tokens": sum(r["output_tokens"] for r in series),
            "avg_words_per_reply": round(sum(words) / len(words), 1),
            "final_context_tokens": series[-1]["input_tokens"],
            "avg_latency_s": round(
                sum(r["latency_ms"] for r in series) / len(series) / 1000, 1
            ),
            "reinjections": sum(1 for r in series if r.get("reinjected")),
        }
        s["total_tokens"] = s["input_tokens"] + s["output_tokens"]
        prices = PRICES.get(model)
        if prices:
            s["est_cost_usd"] = round(
                s["input_tokens"] / 1e6 * prices[0]
                + s["output_tokens"] / 1e6 * prices[1],
                4,
            )
        out[sid] = s
    return out


def chart_png(rows: list[dict], name: str) -> bytes:
    """Render one of CHARTS to PNG bytes."""
    grouped = by_style(rows)
    fig, ax = plt.subplots(figsize=(7, 4.6))

    reinjection_in_legend = False
    for sid, series in grouped.items():
        turns = [r["turn"] for r in series]
        color = _color(sid, grouped)
        if name == "context-growth":
            ys = [r["input_tokens"] for r in series]
            total = sum(r["input_tokens"] + r["output_tokens"] for r in series)
            ax.plot(turns, ys, marker="o", markersize=3.5, linewidth=1.8,
                    color=color, label=f"{sid} (total spend: {total:,} tokens)")
        else:
            ys = [prose_words(r["output"]) for r in series]
            avg = sum(ys) / len(ys)
            ax.plot(turns, ys, marker="o", markersize=3.5, linewidth=1.8,
                    color=color, label=f"{sid} (avg {avg:.0f} words/reply)")
            ax.axhline(avg, color=color, linewidth=0.8, linestyle="--", alpha=0.5)

        nudged = [(t, y) for t, y, r in zip(turns, ys, series) if r.get("reinjected")]
        if nudged:
            ax.scatter([t for t, _ in nudged], [y for _, y in nudged],
                       s=110, facecolors="none", edgecolors="#111111",
                       linewidths=1.6, zorder=5,
                       label=None if reinjection_in_legend else "reinjection")
            reinjection_in_legend = True

    if name == "context-growth":
        ax.set_title("How the conversation grows: context size per turn")
        ax.set_ylabel("Context sent to the model (input tokens)")
    else:
        ax.set_title("Reply length per turn (prose words, code excluded)")
        ax.set_ylabel("Words per reply")
    ax.set_xlabel("Turn")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def _color(style_id: str, grouped: dict) -> str:
    if style_id in STYLE_COLORS:
        return STYLE_COLORS[style_id]
    others = [s for s in grouped if s not in STYLE_COLORS]
    return FALLBACK_COLORS[others.index(style_id) % len(FALLBACK_COLORS)]
