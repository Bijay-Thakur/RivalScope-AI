"""Dev server with safe reload excludes for long research streams.

Usage (from backend/):

    python scripts/dev_server.py

Avoid bare ``uvicorn --reload`` during real-mode research — log/DB writes can
trigger watchfiles reloads and kill in-flight SSE connections.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

import uvicorn  # noqa: E402

RELOAD_EXCLUDES = [
    "**/logs/**",
    "**/data/**",
    "**/eval_results/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
]

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=RELOAD_EXCLUDES,
    )
