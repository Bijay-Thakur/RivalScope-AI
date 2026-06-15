import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "rivalscope.log"
RUN_LOG_FILE = LOG_DIR / "research_runs.jsonl"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def write_run_log(run_id: str, event_type: str, payload: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "event_type": event_type,
        "payload": payload,
    }
    with RUN_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, default=str) + "\n")
