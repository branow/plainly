"""Repo-root paths used across the package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = ROOT / "prompts"
STYLES_DIR = ROOT / "styles"
RUNS_DIR = ROOT / "runs"
