from __future__ import annotations

import json
import os
from pathlib import Path

from .model import RecordStore, TextRecord


APP_DIR_NAME = "Easy-copy"
DATA_DIR_ENV = "EASY_COPY_DATA_DIR"
RECORDS_FILENAME = "records-v1.json"


def default_data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) / APP_DIR_NAME if base else Path.home() / APP_DIR_NAME


class JsonStorage:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[TextRecord]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [TextRecord.from_dict(item) for item in raw]
        except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
            # A damaged or partially written file must not prevent the app starting.
            return []

    def save(self, store: RecordStore) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = json.dumps(
            [record.to_dict() for record in store.records],
            ensure_ascii=False,
            indent=2,
        )
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.path)
