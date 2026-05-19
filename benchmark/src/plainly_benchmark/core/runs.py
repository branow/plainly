"""Run-directory helpers (creating timestamped run dirs)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .paths import RUNS_DIR


def new_run_dir(now: datetime | None = None) -> tuple[str, Path]:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RUNS_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    return ts, out_dir
