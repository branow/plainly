"""Live preview server. Watches runs/ and serves a dashboard.

  uv run preview              # starts on http://localhost:5173
  uv run preview --port 8000
"""

from .app import create_app
from .cli import main

__all__ = ["create_app", "main"]
