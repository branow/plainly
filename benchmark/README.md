# plainly-benchmark

Compare system-prompt styles on the same prompts. Run, score, browse.

## Setup

```sh
cp .env.example .env   # add ANTHROPIC_API_KEY
uv sync
```

## Run

```sh
uv run run-bench                         # all prompts x all styles, 1 sample, haiku
uv run run-bench --samples 3
uv run run-bench --prompts qa-async debug-error --styles baseline caveman
uv run run-bench --model claude-sonnet-4-6
uv run run-bench --backend anthropic_api # default backend: claude_code CLI
uv run run-bench --score                 # run, then score in the same shot
```

Output: `runs/<timestamp>/results.jsonl` + `meta.json` (and `scores.jsonl` if `--score`).

## Score

```sh
uv run score-bench                         # score latest run
uv run score-bench 20260517T083433Z        # score specific run
uv run score-bench --w-cosine 0.8 --w-length 0.2
```

Writes `runs/<ts>/scores.jsonl`. One score per row in `results.jsonl`, merged on `(prompt_slug, style_id, sample)`.

## Growth benchmark (multi-turn)

`run-bench` measures single prompts; `growth-bench` replays the same scripted
25-turn conversation per arm and records how context size, token spend, and
reply length grow turn by turn.

```sh
uv run growth-bench                                  # baseline vs plainly, raw API
uv run growth-bench --style caveman                  # baseline vs another style
uv run growth-bench --style caveman --append-to <ts> # add an arm to an existing run

# Real plugin test: one Claude Code session per arm, actual hooks running
uv run growth-bench --backend claude_code \
  --arm baseline \
  --arm plainly=/path/to/plainly \
  --arm caveman=/path/to/caveman-plugin
```

Two backends:

- **`anthropic_api`** (default) — the style text is the system prompt; plainly's
  refocus loop is emulated in-process with the same thresholds as
  `scripts/refocus.mjs`. Tests the *prompt*.
- **`claude_code`** — each arm is a real Claude Code session via the Agent SDK
  with the plugin loaded (`--arm name=plugin_dir`; bare name = no plugin).
  Tools disabled, user/project settings not loaded, so the only difference
  between arms is the plugin. Its hooks run natively; refocus firings are
  detected from hook events. Tests the *plugin*.

Output: `runs/<ts>/` in the same format as bench runs, with `"type": "growth"`
in `meta.json` and one row per turn (turn number, user message, reply, token
usage, `reinjected` flag). Raw data only — stats and charts live in preview.
`--append-to` reuses the target run's backend/model/max_tokens so arms stay
comparable.

### How scoring works

Each response is compared against the prompt's `ideal_answer` field. Two deterministic signals:

- **`cosine`** — semantic similarity. Both texts embedded with a local `sentence-transformers` model (`all-MiniLM-L6-v2`, ~90MB, downloaded on first use). Cosine of L2-normalized embeddings, so range is `[-1, 1]` (in practice `[0, 1]`).
- **`length_sim`** — tolerance-banded length match. Within `tolerance = max(20, 0.2 * ideal_words)` of the ideal: 1.0. Beyond: linear decay against a floored denominator `max(ideal_words, 50)` so short ideals don't get crushed by small absolute deltas (a 23→50 gap is treated more gently than a 600→1400 gap). Range `[0, 1]`.

Combined: `combined = 0.7 * cosine + 0.3 * length_sim` (weights tunable via `--w-cosine` / `--w-length`).

Scores are deterministic (no LLM judge) and cheap (~80 ms/pair on CPU after model load). Prompts without an `ideal_answer` field are skipped.

## Preview (live dashboard)

```sh
uv run preview                           # http://localhost:5173
uv run preview --port 8000
uv run preview --host 0.0.0.0 --debug
```

Local Flask server. Browse all runs, drill into any single run, see the matrix of styles × prompts plus full response text per sample.

### What you get

- **Index page (`/`)** — table of all runs (timestamp, backend, model, prompt/style/sample counts, row progress). Stale row count flagged in red if `rows < expected`.
- **Run page (`/run/<ts>`)** — growth runs render a per-style summary
  (tokens, final context, words/reply, reinjections, est cost), context-growth
  and reply-length charts generated in memory from the raw rows (reinjected
  turns circled), and per-turn expandable transcripts. Bench runs render:
  - Matrix table: rows = prompts, columns = styles. Each cell shows mean output tokens, mean latency, and (if scored) mean `combined` score with `cosine` / `length_sim` in the tooltip.
  - Per-prompt section: prompt body, ideal answer (if any), and one card per (style, sample) response.
  - Score pill on each response card. Hover for `cosine` / `length_sim` breakdown.
- **Prompts page (`/prompts`)** — corpus browser, built from `prompts/*.json`. Index table (id, slug, title, targets, prompt/ideal word counts), then per-prompt detail card (prompt + ideal answer with expandable formatting, plus any unknown JSON fields auto-rendered).
- **Report page (`/report`)** — cross-run aggregate, built fresh on every request from `runs/` on disk. Three tables:
  - **Style leaderboard** — one row per style, ranked by mean combined score across all runs/models/prompts. Plus mean cosine, length_sim, output tokens, latency, and sample counts.
  - **Style × Model matrix** — mean combined score per `(style, model)` pair. Reveals which style wins on which model.
  - **Per prompt** — mean combined score per `(prompt, style)`. Reveals which style nails which prompt.
  - No static file. No build step. Refresh the page → recomputed.
- **Auto-refresh** — page polls `/api/state` every 2s and reloads when any file under `runs/` changes. Start a benchmark in one terminal, watch results stream into the browser.
- **Expandable long text** — prompts, ideal answers, and responses truncate at a word limit with a "Show more" toggle that expands inline in the same block.

### How preview is built

- `preview/data.py` — read-only loader for `runs/<ts>/{meta.json,results.jsonl,scores.jsonl}` and `prompts/<slug>.json`. Returns dataclasses, no Flask.
- `preview/report.py` — cross-run aggregation. `build_report()` walks every run, score-merges rows, returns a `Report` of `Bucket`s grouped by style / model / (style, model) / (prompt, style). Pure data, no Flask, no caching.
- `preview/app.py` — Flask factory + 5 routes (`/`, `/run/<ts>`, `/prompts`, `/report`, `/api/state`). Registers Jinja filters `word_slice` / `word_count`.
- `preview/cli.py` — argparse entrypoint (`uv run preview`).
- `preview/templates/` — Jinja templates. Pages: `index.html`, `run.html`, `prompts.html`, `report.html`. Partials: `_matrix.html`, `_prompt_section.html`, `_sample_card.html`, `_runs_table.html`. Helpers: `_macros.html` (`expandable_text` for word-truncation + inline expand).
- `preview/static/preview.css` + `auto-refresh.js` — styling and live-reload poll.

Edit a `.html` to change markup; edit `preview.css` to change styling. Truncation thresholds live at the macro call sites (`expandable_text(text, 100)` etc.).

## Layout

- `prompts/*.json` — corpus. Fields: `slug`, `id`, `title`, `targets`, `prompt`, optional `ideal_answer`.
- `styles/*.md` — system prompts under test. Empty file = no system prompt.
- `runs/<ts>/` — per run: `meta.json`, `results.jsonl`, optional `scores.jsonl` (gitignored).
- `src/plainly_benchmark/` — feature folders, one per command:
  - `core/` — shared primitives: `paths.py`, `models.py` (`Row`, `GrowthRow`), `corpus.py` (load prompts/styles), `runs.py` (new run dir), `text.py` (prose word counting).
  - `backends/` — `base.py` + one module per backend (`anthropic_api`, `claude_code`).
  - `bench/` — `run-bench` feature: `runner.py` (run loop), `backends.py` (factory), `cli.py` (argparse).
  - `growth/` — `growth-bench` feature: `conversation.py` (the scripted turns), `backends.py` (API + Claude Code sessions), `runner.py`, `cli.py`.
  - `score/` — `score-bench` feature: `scorer.py` (`Scorer`, `score_run`, `load_scores`), `cli.py`.
  - `preview/` — `preview` feature: `app.py` (Flask factory + routes), `data.py` (run loader), `report.py` (cross-run aggregates), `cli.py`, `templates/`, `static/`.

## Typical workflow

```sh
uv run run-bench --samples 3 &           # kick off benchmark
uv run preview                           # open http://localhost:5173, watch live
# when done:
uv run score-bench                         # add scores to latest run
# preview auto-refreshes; score column + pills appear
```
