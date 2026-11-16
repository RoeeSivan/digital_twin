"""JSON audit log: a file holds a list of QuestionRecords, one per user question.

- The chat app writes one file per run: logs/session_<YYYYmmdd_HHMMSS>.json.
- The scenario script (Part D) writes logs/scenario_<n>.json.
Hebrew is stored as readable text (ensure_ascii=False).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from twin.config import LOGS_DIR
from twin.schemas import QuestionRecord

_RECORDS = TypeAdapter(list[QuestionRecord])


def session_log_path(started: datetime | None = None, logs_dir: Path = LOGS_DIR) -> Path:
    started = started or datetime.now()
    return logs_dir / f"session_{started:%Y%m%d_%H%M%S}.json"


def read_records(path: Path) -> list[QuestionRecord]:
    """All records in a log file; an empty list if the file does not exist yet."""
    if not path.exists():
        return []
    return _RECORDS.validate_json(path.read_bytes())


def write_records(path: Path, records: list[QuestionRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [record.model_dump(mode="json") for record in records]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_record(path: Path, record: QuestionRecord) -> None:
    write_records(path, [*read_records(path), record])
